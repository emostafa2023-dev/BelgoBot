from bs4 import BeautifulSoup
import json
import re


def parse(html) -> dict:

    soup = BeautifulSoup(html, "html.parser")

    tabla = soup.find("table", {"id": "shedule"})

    resultado = {}

    dia_actual = None

    for tr in tabla.find_all("tr"):

        # Detectar encabezado de día
        h3 = tr.find("span", class_="h3")

        if h3:
            texto_dia = h3.get_text(" ", strip=True)

            # Limpiar espacios extra
            texto_dia = re.sub(r"\s+", " ", texto_dia)

            dia_actual = texto_dia
            resultado[dia_actual] = []
            continue


        # Detectar filas de horarios
        td_num = tr.find("td", {"id": "num"})
        td_time = tr.find("td", {"id": "time"})

        lessons = tr.find_all("td", {"id": "lesson"})

        if td_num and td_time and len(lessons) >= 2 and dia_actual:

            numero = td_num.get_text(" ", strip=True)
            horario = td_time.get_text(" ", strip=True)

            tipo = lessons[0].get_text(" ", strip=True)
            materia = lessons[1].get_text(" ", strip=True)

            resultado[dia_actual].append({
                "numero": numero,
                "horario": horario,
                "tipo": tipo,
                "materia": materia
            })

    # Mostrar JSON bonito
    #print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return resultado