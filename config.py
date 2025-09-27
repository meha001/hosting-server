import os

class Config:
    SECRET_KEY = 'rkmlkmkklmfmrmgrg'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'user_files')
    WTF_CSRF_ENABLED = True