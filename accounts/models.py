from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN='ADMIN','Administrateur'
        FREELANCE='FREELANCE','Freelancer'
        CLIENT='CLIENT','Particulier/Entreprise'

    role=models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT
    )
    phone_number= models.CharField(max_length=20,blank=True,null=True)
    avatar=models.ImageField(upload_to='avatars/',blank=True,null=True)

    def save(self,*args,**kwargs):
        if self.is_superuser:
            self.role=self.role.ADMIN.value
        return super().save(*args,**kwargs)
# Create your models here.


class FreelanceProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='freelance_profile')
    title=models.CharField(max_length=100,help_text='ex: développeur fullstack python')
    bio=models.TextField(blank=True)
    skills=models.CharField(max_length=250,help_text="competences séparéés par des virgules")
    portfolio_url=models.URLField(blank=True,null=True)
    github_url=models.URLField(blank=True,null=True)
    hourly_rate=models.DecimalField(max_digits=10,decimal_places=2,help_text="tarif horaire indicatif")

    is_verified=models.BooleanField(default=False)
    create_at=models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"profile Freelance de {self.user.username}"



class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    compagny_name = models.CharField(max_length=100,blank=True,null=True, help_text='laissez vide si particulier')
    description = models.TextField(blank=True)
    website = models.URLField(blank=True, null=True)
    create_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"profile client de {self.user.username}"

