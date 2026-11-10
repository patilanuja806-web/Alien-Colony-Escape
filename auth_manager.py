"""
Handles JSON file-based local account creation and validation.
"""
import os
import json
import hashlib

_BASE = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(_BASE, "colony_users.json")
LEGACY_FILE = os.path.join(_BASE, "colony_user.json")  # old file name, still read


def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class AuthManager:
    def __init__(self):
        self.accounts = self._load()

    def _read(self, path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _load(self):
        accounts = self._read(LEGACY_FILE)
        accounts.update(self._read(DATABASE_FILE))
        return accounts

    def _save(self):
        try:
            with open(DATABASE_FILE, "w") as f:
                json.dump(self.accounts, f, indent=4)
        except OSError:
            pass

    def login(self, username, password):
        user = username.strip().lower()
        if user in self.accounts and self.accounts[user] == hash_pass(password):
            return True, "Login successful! Identity confirmed."
        return False, "Access Denied: Incorrect credentials."

    def register(self, username, password):
        user = username.strip().lower()
        if len(user) < 3 or len(password) < 3:
            return False, "Error: Username/Password must be at least 3 chars."
        if user in self.accounts:
            return False, "Record exists: Officer already registered."

        self.accounts[user] = hash_pass(password)
        self._save()
        return True, "Registration successful! You may now sign in."