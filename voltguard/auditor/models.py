from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Appliance(models.Model):
    project = models.ForeignKey(Project, related_name='appliances', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    power_watts = models.FloatField(help_text="Power in Watts (P)")
    length_m = models.FloatField(help_text="Length of wire in meters (L)")

    def __str__(self):
        return f"{self.name} ({self.power_watts}W)"
