import pyotp

secret = pyotp.random_base32()
totp = pyotp.TOTP(secret)

print(f"Verify empty string: {totp.verify('')}")
print(f"Verify None: {totp.verify(None)}")
print(f"Verify '000000': {totp.verify('000000')}")
