# Generated by Django 5.2.4 on 2025-07-23 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_variation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='variation',
            name='variation_category',
            field=models.CharField(choices=[('color', 'color'), ('size', 'size'), ('taste', 'taste')], max_length=200),
        ),
    ]
