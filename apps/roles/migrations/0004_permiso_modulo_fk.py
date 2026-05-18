from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0003_permiso_icono_permiso_ruta_permiso_submodulo'),
        ('tenants', '0002_modulo_icono_modulo_ruta'),
    ]

    operations = [
        migrations.AddField(
            model_name='permiso',
            name='modulo_nuevo',
            field=models.ForeignKey(
                to='tenants.Modulo',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='permisos',
                null=True,
                blank=True,
            ),
        ),
        migrations.RemoveField(
            model_name='permiso',
            name='modulo',
        ),
        migrations.RenameField(
            model_name='permiso',
            old_name='modulo_nuevo',
            new_name='modulo',
        ),
    ]
