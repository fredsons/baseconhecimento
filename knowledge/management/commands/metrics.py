import json
from collections import Counter
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from knowledge.models import SearchMiss,Feedback
class Command(BaseCommand):
    def handle(self,*args,**opts):
        counts=Counter()
        for path in settings.DATA_DIR.glob('audit.log*'):
            for line in path.open(encoding='utf-8'):
                try:
                    row=json.loads(line)
                    if row['event']=='view': counts[row['article']]+=1
                except (ValueError,KeyError): pass
        self.stdout.write('Artigos mais vistos (id, acessos): '+str(counts.most_common(20)))
        self.stdout.write('Buscas sem resultado: '+str(list(SearchMiss.objects.values('query').annotate(total=Count('pk')).order_by('-total')[:20])))
        self.stdout.write('Feedback: '+str(list(Feedback.objects.values('article_id','helpful').annotate(total=Count('pk')))))
