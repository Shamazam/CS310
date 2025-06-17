# insert_admin.py

from db import setup_database, create_user

# Step 1: Set up the tables (just in case)
setup_database()

# Step 2: Create admin user
admin_id = "admin001"
admin_name = "Super Admin"
admin_password = "adminpass123"  # Choose a strong password
admin_role = "admin"

create_user(admin_id, admin_name, admin_password, admin_role)
print("Admin user created successfully!")
