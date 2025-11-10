# Generated migration for instructors app
# This migration references existing tables created by the legacy app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('collections', '0001_initial'),
    ]

    operations = [
        # These tables already exist in the database from the legacy app
        # We use CreateModel with Meta.db_table to reference them without creating
        migrations.CreateModel(
            name='ClassPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('difficulty_level', models.CharField(choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')], db_index=True, max_length=20)),
                ('estimated_duration', models.IntegerField(blank=True, help_text='Estimated duration in minutes', null=True)),
                ('instructor_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('instructor', models.ForeignKey(limit_choices_to={'is_instructor': True}, on_delete=django.db.models.deletion.CASCADE, related_name='class_plans', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Class Plan',
                'verbose_name_plural': 'Class Plans',
                'db_table': 'class_plans',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ClassPlanSequence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sequence_order', models.IntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('estimated_time', models.IntegerField(blank=True, help_text='Estimated time for this sequence in minutes', null=True)),
                ('choreography', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_sequences', to='collections.savedchoreography')),
                ('class_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sequences', to='instructors.classplan')),
            ],
            options={
                'verbose_name': 'Class Plan Sequence',
                'verbose_name_plural': 'Class Plan Sequences',
                'db_table': 'class_plan_sequences',
                'ordering': ['sequence_order'],
                'unique_together': {('class_plan', 'sequence_order')},
            },
        ),
    ]
