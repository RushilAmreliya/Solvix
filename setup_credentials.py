"""
NASA Earthdata Secure Credential Setup
Writes your credentials to ~/.netrc (never stored in the repo).

Run once:
    python setup_credentials.py
"""
import os
import sys
import stat
import getpass
import platform

NETRC_PATH = os.path.join(os.path.expanduser("~"), "_netrc" if platform.system() == "Windows" else ".netrc")
NASA_HOST  = "urs.earthdata.nasa.gov"

def setup():
    print("=" * 60)
    print("  NASA Earthdata Secure Credential Setup")
    print("=" * 60)
    print(f"\nThis script writes your credentials to:")
    print(f"  {NETRC_PATH}")
    print("\nYour credentials will NEVER be stored in the project repo.")
    print("The file is already in .gitignore.\n")

    username = input("Enter your NASA Earthdata username: ").strip()
    password = getpass.getpass("Enter your NASA Earthdata password: ")

    if not username or not password:
        print("\n[ERROR] Username and password cannot be empty.")
        sys.exit(1)

    # Read existing entries to avoid duplicates
    existing_lines = []
    if os.path.exists(NETRC_PATH):
        with open(NETRC_PATH, "r") as f:
            lines = f.readlines()
        # Remove any existing NASA Earthdata entry
        skip = False
        for line in lines:
            if f"machine {NASA_HOST}" in line:
                skip = True
            elif line.startswith("machine ") and skip:
                skip = False
            if not skip:
                existing_lines.append(line)

    # Write updated netrc
    nasa_block = (
        f"machine {NASA_HOST}\n"
        f"login {username}\n"
        f"password {password}\n"
    )
    with open(NETRC_PATH, "w") as f:
        f.writelines(existing_lines)
        f.write("\n" + nasa_block)

    # Restrict permissions on Unix/Mac (Windows doesn't support chmod the same way)
    if platform.system() != "Windows":
        os.chmod(NETRC_PATH, stat.S_IRUSR | stat.S_IWUSR)

    print(f"\n[OK] Credentials saved to {NETRC_PATH}")
    print("\nNow verify the connection:")
    print("  python -c \"import earthaccess; earthaccess.login(strategy='netrc'); print('AUTH OK')\"")


if __name__ == "__main__":
    setup()
