from django.db import models

# Create your models here.

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=20)
    user_passwd = models.CharField(max_length=20)
    user_email = models.CharField(max_length=20)