from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class DailyQuota(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    attempts_count = models.PositiveIntegerField(default=0)
    messages_count = models.PositiveIntegerField(default=0)  

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.email} - {self.date}"
