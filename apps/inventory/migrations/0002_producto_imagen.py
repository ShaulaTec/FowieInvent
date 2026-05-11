# apps/inventory/migrations/0002_producto_imagen.py
from django.db import migrations, models
import apps.inventory.models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='imagen',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=apps.inventory.models._ruta_imagen_producto,
                help_text='Imagen del producto (opcional).',
            ),
        ),
    ]
