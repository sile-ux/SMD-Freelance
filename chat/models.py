# chat/models.py
from typing import Any

from django.db import models
from django.conf import settings

class Thread(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_threads')
    freelance = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='freelance_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted_by_client = models.BooleanField(default=False)
    is_deleted_by_freelance = models.BooleanField(default=False)

    class Meta:
        unique_together = ('client', 'freelance')

    def __str__(self):
        return f"Discussion entre {self.client.username} et {self.freelance.username}"

    def is_deleted_by(self, user):
        if user == self.client:
            return self.is_deleted_by_client
        return self.is_deleted_by_freelance

    def is_blocked(self, user):
        """Vérifie si l'utilisateur a bloqué l'autre dans ce thread"""
        other = self.freelance if user == self.client else self.client
        return BlockedUser.objects.filter(blocker=user, blocked=other).exists()

    def other_user(self, user):
        return self.freelance if user == self.client else self.client


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat_files/', blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message de {self.sender.username} à {self.created_at}"


class BlockedUser(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        verbose_name = "Utilisateur bloqué"
        verbose_name_plural = "Utilisateurs bloqués"

    def __str__(self):
        return f"{self.blocker} a bloqué {self.blocked}"
