from werkzeug.security import generate_password_hash

password = 'password123'

print("-- Password hashes for password123:")
print(f"User 1: {generate_password_hash(password)}")
print(f"User 2: {generate_password_hash(password)}")
print(f"Subscriber 1: {generate_password_hash(password)}")
print(f"Subscriber 2: {generate_password_hash(password)}")
print(f"Admin 2: {generate_password_hash(password)}")
print(f"Admin 3: {generate_password_hash(password)}")

