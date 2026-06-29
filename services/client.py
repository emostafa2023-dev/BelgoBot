import requests
import ast
import utilities.parser as parser

class Client:
    def getGroups(self) -> list:
        # belgu
        responseGroups=requests.get('https://bsuedu.ru/bsu/education/schedule/groups/group_json.php?fak=104&frm=2')

        #print(responseGroups.status_code)
        if responseGroups.status_code != 200:
            return []
        
        #print(responseGroups.text)
        data = ast.literal_eval(responseGroups.text)

        lista = [x[0] for x in data]

        #print(lista)
        return lista

    # 12002308 , 2206202628062026
    # group , ddmmYYYY , ddmmYYYY
    def getRaspisanie(self,group, week_start,week_end) -> dict:
        print('group: '+ group+'week: '+week_start+week_end)
        responseRaspisanie = requests.post('https://bsuedu.ru/bsu/education/schedule/groups/show_schedule.php',
                            data={'group': group,'week':week_start+week_end})

        #print(responseRaspisanie.status_code)
        if responseRaspisanie.status_code != 200:
            return {}

        #print(responseRaspisanie.text)
        return parser.parse(responseRaspisanie.text)
