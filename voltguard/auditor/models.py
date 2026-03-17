from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    total_load = models.FloatField(default=0.0, help_text="Total Connected Load (W)")
    phase_type = models.CharField(max_length=20, default='1-Phase')

    def __str__(self):
        return self.name

class Appliance(models.Model):
    APPLIANCE_TYPES = [
        ('Motor/AC', 'Motor/AC'),
        ('Light', 'Light'),
        ('Standard', 'Standard'),
    ]
    
    project = models.ForeignKey(Project, related_name='appliances', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    appliance_type = models.CharField(max_length=20, choices=APPLIANCE_TYPES, default='Standard')
    quantity = models.IntegerField(default=1, help_text="Number of identical items on this circuit")
    power_watts = models.FloatField(help_text="Real Power per item in Watts (P)")
    power_factor = models.FloatField(default=1.0, help_text="Power Factor (0.0 to 1.0)")
    length_m = models.FloatField(help_text="Length of wire in meters (L)")

    def __str__(self):
        return f"{self.quantity}x {self.name} ({self.power_watts}W @ {self.power_factor} PF)"
