# Generated migration for security features

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_admin'),
    ]

    operations = [
        # Ajouter le champ verification_token_created_at au modele User
        migrations.AddField(
            model_name='user',
            name='verification_token_created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Creer le modele LoginAttempt pour tracking anti-bruteforce
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField()),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('successful', models.BooleanField(default=False)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['ip_address', 'attempted_at'], name='users_login_ip_addr_idx'),
                    models.Index(fields=['email', 'attempted_at'], name='users_login_email_idx'),
                ],
            },
        ),
    ]
