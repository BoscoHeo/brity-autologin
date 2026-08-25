import sys
sys.path.insert(0, '.')
from encryptor import encrypt, decrypt
import os

test_pw = 'TestPassword123!'
token = encrypt(test_pw)
result = decrypt(token)

print('원문:    ', test_pw)
print('암호화:  ', token[:40] + '...')
print('복호화:  ', result)
print('일치:    ', 'PASS' if test_pw == result else 'FAIL')
print('key.bin:', '생성됨' if os.path.exists('key.bin') else '없음')
