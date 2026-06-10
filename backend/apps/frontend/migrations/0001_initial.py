from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='SimulationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=50)),
                ('incident', models.CharField(max_length=300)),
                ('severity', models.CharField(default='critical', max_length=20)),
                ('perceiver_msg', models.TextField()),
                ('perceiver_conf', models.FloatField(default=0.94)),
                ('planner_cause', models.TextField(default='')),
                ('planner_plan', models.TextField()),
                ('recoverer_action', models.TextField()),
                ('recoverer_result', models.TextField()),
                ('guardian_sec', models.TextField(default='')),
                ('guardian_audit', models.TextField()),
                ('incident_id', models.CharField(default='INC-000', max_length=20)),
                ('groq_model', models.CharField(default='llama-3.3-70b-versatile', max_length=100)),
                ('groq_powered', models.BooleanField(default=False)),
                ('heal_time_ms', models.IntegerField(default=1240)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
