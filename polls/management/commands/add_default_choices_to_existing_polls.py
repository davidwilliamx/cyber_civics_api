from django.core.management.base import BaseCommand
from django.db.models import Q # Importar Q para consultas complexas

from polls.models import Poll, Choice

class Command(BaseCommand):
    help = 'Adds default "Concordo", "Discordo", "Neutro" choices to existing polls/proposals that do not have them.'

    def handle(self, *args, **options):
        default_texts = ["Concordo", "Discordo", "Neutro"]
        polls_updated_count = 0
        choices_added_count = 0

        # Encontrar todas as enquetes/propostas existentes
        all_polls = Poll.objects.all()
        total_polls = all_polls.count()

        self.stdout.write(self.style.SUCCESS(f'Checking {total_polls} existing polls/proposals for missing default choices...'))

        for poll in all_polls:
            self.stdout.write(f'Processing Poll "{poll.title}" (ID: {poll.id})...', ending='')

            # Obter as opções padrão que JÁ existem para esta enquete
            existing_default_choices = Choice.objects.filter(
                poll=poll,
                choice_text__in=default_texts
            ).values_list('choice_text', flat=True)

            # Identificar quais opções padrão estão faltando
            missing_default_texts = [
                text for text in default_texts if text not in existing_default_choices
            ]

            if missing_default_texts:
                # Criar as opções padrão que estão faltando
                choices_to_create = [
                    Choice(poll=poll, choice_text=text) for text in missing_default_texts
                ]
                created_choices = Choice.objects.bulk_create(choices_to_create)

                self.stdout.write(self.style.SUCCESS(f' Added {len(created_choices)} missing default choice(s): {", ".join(missing_default_texts)}'))
                polls_updated_count += 1
                choices_added_count += len(created_choices)
            else:
                self.stdout.write(self.style.SUCCESS(' All default choices already exist.'))

        self.stdout.write(self.style.SUCCESS(
            f'\nFinished adding default choices.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total polls/proposals updated: {polls_updated_count}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total default choices added: {choices_added_count}'
        ))