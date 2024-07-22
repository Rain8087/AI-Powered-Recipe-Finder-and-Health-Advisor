# Author: Jordan Lau Jing Hong
# Student ID: TP064941
# Purpose: FYP

from django.db import models

class myUser(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]

    PREGNANCY_CHOICES = [
        ('T', 'True'),
        ('F', 'False'),
    ]

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    pregnancy = models.CharField(max_length=1, choices=PREGNANCY_CHOICES, blank=True, null=True)
    allergies = models.JSONField(default=list, blank=True)
    chronic_illnesses = models.JSONField(default=list, blank=True)
    dietary_preferences = models.JSONField(default=list, blank=True)
    religious_restrictions = models.CharField(max_length=100, blank=True, null=True)
    history = models.JSONField(default=list, blank=True)
    shopping_list = models.JSONField(default=list, blank=True) 