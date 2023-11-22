from bkcrypto.symmetric import interceptors
from bkcrypto.symmetric.ciphers.base import BaseSymmetricCipher, EncryptionMetadata


class SymmetricInterceptor(interceptors.BaseSymmetricInterceptor):
    AES_BLOCK_SIZE = 16

    @classmethod
    def pad_it(cls, plaintext):
        """将密文填充为16整数倍"""
        count = cls.AES_BLOCK_SIZE - len(plaintext) % cls.AES_BLOCK_SIZE
        flag = chr(cls.AES_BLOCK_SIZE - len(plaintext) % cls.AES_BLOCK_SIZE)
        return plaintext + count * flag

    @classmethod
    def unpad_it(cls, plaintext):
        """将填充文本解包"""
        return plaintext[: -ord(plaintext[-1])]

    @classmethod
    def before_encrypt(cls, plaintext: str, **kwargs) -> str:
        return cls.pad_it(plaintext)

    @classmethod
    def after_decrypt(cls, plaintext: str, **kwargs) -> str:
        return cls.unpad_it(plaintext)

    @classmethod
    def after_encrypt(cls, ciphertext: str, **kwargs) -> str:
        """在加密后，需要去掉加密模块元数据----兼容以前的AES加密模式"""
        cipher: BaseSymmetricCipher = kwargs["cipher"]
        ciphertext_bytes, __ = cipher.extract_encryption_metadata(ciphertext)
        return cipher.config.convertor.to_string(ciphertext_bytes)

    @classmethod
    def before_decrypt(cls, ciphertext: str, **kwargs) -> str:
        """在解密后，需要加上加密模块元数据----兼容新的SDK解密模式"""
        cipher: BaseSymmetricCipher = kwargs["cipher"]
        return cipher.combine_encryption_metadata(
            cipher.config.convertor.from_string(ciphertext), EncryptionMetadata(cipher.config.iv)
        )
