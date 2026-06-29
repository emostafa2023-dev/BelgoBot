from services.client import Client


cli = Client()
groups = cli.getRaspisanie('12002308','20062026','27062026')


for x in groups:
    print('DIA: '+x)
    dias = groups[x]
    for d in dias:
        print('numero: '+str(d['numero']))
        print('horario: '+str(d['horario']))
        print('tipo: '+str(d['tipo']))
        print('materia: '+str(d['materia']))