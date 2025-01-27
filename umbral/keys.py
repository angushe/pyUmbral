import os
from typing import Tuple

from .curve_scalar import CurveScalar
from .curve_point import CurvePoint
from .dem import kdf
from .hashing import Hash
from .serializable import Serializable


class SecretKey(Serializable):
    """
    Umbral secret (private) key.
    """

    __SERIALIZATION_INFO = b"SECRET_KEY"

    def __init__(self, scalar_key: CurveScalar):
        self._scalar_key = scalar_key
        # Cached public key. Access it via `PublicKey.from_secret_key()` -
        # it may be removed later.
        # We are assuming here that there will be on average more calls to
        # `PublicKey.from_secret_key()` than secret key instantiations.
        self._public_key_point = CurvePoint.generator() * self._scalar_key

    @classmethod
    def random(cls) -> 'SecretKey':
        """
        Generates a random secret key and returns it.
        """
        return cls(CurveScalar.random_nonzero())

    def __eq__(self, other):
        return self._scalar_key == other._scalar_key

    def __str__(self):
        return f"{self.__class__.__name__}:..."

    def __hash__(self):
        raise RuntimeError("Hashing secret objects is not secure")

    def secret_scalar(self):
        return self._scalar_key

    @classmethod
    def __take__(cls, data: bytes) -> Tuple['SecretKey', bytes]:
        (scalar_key,), data = cls.__take_types__(data, CurveScalar)
        return cls(scalar_key), data

    def __bytes__(self) -> bytes:
        return bytes(self._scalar_key)


class PublicKey(Serializable):
    """
    Umbral public key.
    """

    def __init__(self, point_key: CurvePoint):
        self._point_key = point_key

    def point(self):
        return self._point_key

    @classmethod
    def from_secret_key(cls, sk: SecretKey) -> 'PublicKey':
        """
        Creates the public key corresponding to the given secret key.
        """
        return cls(sk._public_key_point)

    @classmethod
    def __take__(cls, data: bytes) -> Tuple['PublicKey', bytes]:
        (point_key,), data = cls.__take_types__(data, CurvePoint)
        return cls(point_key), data

    def __bytes__(self) -> bytes:
        return bytes(self._point_key)

    def __str__(self):
        return f"{self.__class__.__name__}:{bytes(self).hex()[:16]}"

    def __eq__(self, other):
        return self._point_key == other._point_key

    def __hash__(self) -> int:
        return hash((self.__class__, bytes(self)))


class SecretKeyFactory(Serializable):
    """
    This class handles keyring material for Umbral, by allowing deterministic
    derivation of :py:class:`SecretKey` objects based on labels.

    Don't use this key material directly as a key.
    """

    _KEY_SEED_SIZE = 64
    _DERIVED_KEY_SIZE = 64

    def __init__(self, key_seed: bytes):
        self.__key_seed = key_seed

    @classmethod
    def random(cls) -> 'SecretKeyFactory':
        """
        Creates a random factory.
        """
        return cls(os.urandom(cls._KEY_SEED_SIZE))

    def secret_key_by_label(self, label: bytes) -> SecretKey:
        """
        Creates a :py:class:`SecretKey` from the given label.
        """
        tag = b"KEY_DERIVATION/" + label
        key = kdf(self.__key_seed, self._DERIVED_KEY_SIZE, info=tag)

        digest = Hash(tag)
        digest.update(key)
        scalar_key = CurveScalar.from_digest(digest)

        return SecretKey(scalar_key)

    @classmethod
    def __take__(cls, data: bytes) -> Tuple['SecretKeyFactory', bytes]:
        key_seed, data = cls.__take_bytes__(data, cls._KEY_SEED_SIZE)
        return cls(key_seed), data

    def __bytes__(self) -> bytes:
        return bytes(self.__key_seed)

    def __str__(self):
        return f"{self.__class__.__name__}:..."

    def __hash__(self):
        raise RuntimeError("Hashing secret objects is not secure")
