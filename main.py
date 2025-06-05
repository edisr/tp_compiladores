import re
import json
from collections import defaultdict
from textblob import TextBlob  # type: ignore # Para análisis de sentimiento simple

class Token:
    def __init__(self, lexema, tipo):
        self.lexema = lexema
        self.tipo = tipo
    def __repr__(self):
        return f"Token('{self.lexema}', '{self.tipo}')"

class Tokenizador:
    def __init__(self):
        self.patrones = [
            ('NUMERO', r'\b\d+(\.\d+)?\b'),
            ('PALABRA', r'\b[A-Za-záéíóúñÁÉÍÓÚÑ]+\b'),
            ('PUNTUACION', r'[.,;:!?]'),
            ('ESPACIO', r'\s+'),
            ('OTRO', r'.'),
        ]
        patrones_union = '|'.join(f'(?P<{n}>{p})' for n, p in self.patrones)
        self.patron_compilado = re.compile(patrones_union)

    def tokenizar(self, texto):
        tokens = []
        for match in self.patron_compilado.finditer(texto):
            tipo = match.lastgroup
            lexema = match.group()
            if tipo != 'ESPACIO':
                tokens.append(Token(lexema, tipo))
        return tokens

def distancia_levenshtein(s1, s2):
    if len(s1) < len(s2):
        return distancia_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def distancia_hamming(s1, s2):
    max_len = max(len(s1), len(s2))
    s1 = s1.ljust(max_len)
    s2 = s2.ljust(max_len)
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

def detectar_lexema(lexema, tabla_simbolos):
    lexema_lower = lexema.lower()
    if lexema_lower in tabla_simbolos:
        token = tabla_simbolos[lexema_lower]['token']
        puntuacion = tabla_simbolos[lexema_lower].get('sentimiento', None)
        print(f"Lexema válido: '{lexema}' Token: {token} Sentimiento: {puntuacion}")
        return lexema, token, puntuacion

    print(f"\nLexema candidato no encontrado: '{lexema}'")

    # Generar sugerencias desde el inicio para que estén disponibles siempre
    dist_lev = [(palabra, distancia_levenshtein(lexema_lower, palabra)) for palabra in tabla_simbolos]
    dist_lev.sort(key=lambda x: x[1])
    dist_ham = [(palabra, distancia_hamming(lexema_lower, palabra)) 
                for palabra in tabla_simbolos if abs(len(lexema) - len(palabra)) <= 1]
    dist_ham.sort(key=lambda x: x[1])
    sugerencias = set()
    sugerencias.update([p for p, d in dist_lev[:3]])
    sugerencias.update([p for p, d in dist_ham[:3]])
    sugerencias = list(sugerencias)  # Para indexar

    if sugerencias:
        print("Sugerencias de palabras similares:")
        for i, s in enumerate(sugerencias, start=1):
            print(f"{i}. {s}")
    else:
        print("No se encontraron sugerencias similares.")

    eleccion = input("Seleccione el número de la palabra correcta o presione Enter para ignorar: ").strip()
    if eleccion.isdigit():
        indice = int(eleccion) - 1
        if 0 <= indice < len(sugerencias):
            seleccion = sugerencias[indice]
            print(f"Has seleccionado: {seleccion}")
            token = tabla_simbolos[seleccion]['token']
            puntuacion = tabla_simbolos[seleccion].get('sentimiento', None)
            return seleccion, token, puntuacion

    # Si no selecciona nada o no hay sugerencias válidas
    respuesta = input(f"¿Desea registrar '{lexema}' como un nuevo lexema válido? (s/n): ").strip().lower()
    if respuesta == 's':
        token = input("Ingrese el tipo de token que representa: ").strip()
        while True:
            try:
                puntuacion = float(input("Ingrese la puntuación de sentimiento (-3 a 3): ").strip())
                break
            except ValueError:
                print("Ingrese un número válido para la puntuación.")
        tabla_simbolos[lexema_lower] = {
            'token': token,
            'sentimiento': puntuacion
        }
        # Guardar sin sobrescribir (modo 'r+' para mantener contenido anterior)
        try:
            with open('bd.txt', 'r+', encoding='utf-8') as f:
                data = json.load(f)
                data.update(tabla_simbolos)
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=4)
        except FileNotFoundError:
            with open('bd.txt', 'w', encoding='utf-8') as f:
                json.dump(tabla_simbolos, f, ensure_ascii=False, indent=4)

        print(f"Nuevo lexema registrado: {lexema_lower} → Token: {token}, Sentimiento: {puntuacion}")
        return lexema_lower, token, puntuacion

    return None, None, None

def verificar_protocolo_con_bd(texto, tokens_protocolo):
    texto = texto.lower()
    resultado = {
        "saludo": False,
        "identificacion_cliente": False,
        "palabras_no_permitidas": False,
        "despedida": False
    }

    if any(frase in texto for frase in tokens_protocolo["SALUDO"]):
        resultado["saludo"] = True

    if any(frase in texto for frase in tokens_protocolo["IDENTIFICACION_CLIENTE"]):
        resultado["identificacion_cliente"] = True

    if any(frase in texto for frase in tokens_protocolo["NO_PERMITIDA"]):
        resultado["palabras_no_permitidas"] = True

    if any(frase in texto for frase in tokens_protocolo["DESPEDIDA"]):
        resultado["despedida"] = True

    return resultado

def cargar_lexemas_desde_bd(archivo="bd.txt"):
    tokens_protocolo = defaultdict(list)
    with open(archivo, "r", encoding="utf-8") as f:
        data = json.load(f)
        for lexema, atributos in data.items():
            tipo_token = atributos.get("token", "").upper()
            if tipo_token in [
                "SALUDO",
                "IDENTIFICACION_CLIENTE",
                "NO_PERMITIDA",
                "DESPEDIDA"
            ]:
                tokens_protocolo[tipo_token].append(lexema.lower())
    return tokens_protocolo



def main():
    with open('bd.txt', 'r', encoding='utf-8') as f:
        tabla_simbolos = json.load(f)

    with open('transcripcion2.txt', 'r', encoding='utf-8') as tex:
        texto = tex.read()

    tokenizador = Tokenizador()
    tokens = tokenizador.tokenizar(texto)

    print("\nTokens detectados:")
    for t in tokens:
        print(t)

    puntuaciones = []  # Aquí guardamos los sentimientos válidos
    palabras_positivas = []
    palabras_negativas = []
    max_positiva = ("", float('-inf'))
    max_negativa = ("", float('inf'))

    print("\nDetección y validación de lexemas:")
    for t in tokens:
        if t.tipo == 'PALABRA':
            lexema_validado, _, puntuacion = detectar_lexema(t.lexema, tabla_simbolos)
            if puntuacion is not None:
                puntuaciones.append(puntuacion)
                if puntuacion > 0:
                    palabras_positivas.append((lexema_validado, puntuacion))
                    if puntuacion > max_positiva[1]:
                        max_positiva = (lexema_validado, puntuacion)
                elif puntuacion < 0:
                    palabras_negativas.append((lexema_validado, puntuacion))
                    if puntuacion < max_negativa[1]:
                        max_negativa = (lexema_validado, puntuacion)

        # --- Resultados y Reporte Final ---

    print("\n================== REPORTE FINAL ==================")

    # Análisis de Sentimiento
    print("\n1. Detección de Sentimiento:")
    if puntuaciones:
        total = sum(puntuaciones)
        sentimiento_general = "Positivo" if total > 0 else "Negativo" if total < 0 else "Neutral"
        print(f"Sentimiento general: {sentimiento_general} ({total:+.1f})")
        print(f"Palabras positivas: {len(palabras_positivas)}")
        if palabras_positivas:
            print(f"Palabra más positiva: {max_positiva[0]}, +{max_positiva[1]}")
        print(f"Palabras negativas: {len(palabras_negativas)}")
        if palabras_negativas:
            print(f"Palabra más negativa: {max_negativa[0]}, {max_negativa[1]}")
    else:
        print("No se detectaron palabras con puntuación de sentimiento.")

    # Cargar tokens del protocolo desde la base de datos
    tokens_protocolo = cargar_lexemas_desde_bd()
    # Verificación del protocolo de atención
    resultado = verificar_protocolo_con_bd(texto, tokens_protocolo)

    # Verificación de protocolo
    print("\n2. Verificación del Protocolo de Atención:")
    etiquetas = {
        "saludo": "Fase de saludo",
        "identificacion_cliente": "Identificación del cliente",
        "palabras_no_permitidas": "Uso de palabras rudas",
        "despedida": "Despedida amable"
    }
    for clave, texto in etiquetas.items():
        estado = resultado[clave]
        print(f"{texto}: {'OK' if estado else 'Faltante' if clave != 'palabras_no_permitidas' else 'Ninguna detectada' if not estado else 'Detectada'}")

    print("\n===================================================")

if __name__ == "__main__":
    main()

