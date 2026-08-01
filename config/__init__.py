""" from .celery import app as celery_app
__all__ = ('celery_app',) """

# config/__init__.py
import pymysql

pymysql.install_as_MySQLdb()

from .celery import app as celery_app

__all__ = ('celery_app',)