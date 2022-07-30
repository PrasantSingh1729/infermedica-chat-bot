from django.db import models

class Destination(models.Model):    
    name= models.CharField(max_length=100)
    img= models.ImageField(upload_to='pics')
    desc= models.TextField()
    price= models.IntegerField()
    offer= models.BooleanField(default=False)
class Chat:    
    by : str
    text : str

class detail():
    phnno: int
    age: int
    sex: str
    name: str
# Create your models here.
