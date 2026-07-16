with open("app/core/dependency.py", "r") as f:
    content = f.read()
new_content = content.replace(
    'status = permission_status.get((method, matched_path))',
    'status = permission_status.get((method, matched_path))\n        print(f"DEBUG has_perm: {method} {matched_path} in {permission_status}")'
)
with open("app/core/dependency.py", "w") as f:
    f.write(new_content)
