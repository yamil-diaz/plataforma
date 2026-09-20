# -*- coding: utf-8 -*-
"""
Full cover inventory for AeternumLibrary.
Cross-references production API with seed data to build complete classification.
"""
import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

# Load production books
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'production_books.json'), encoding='utf-8') as f:
    prod_books = json.load(f)

# Build lookup from production
prod_by_id = {b['id']: b for b in prod_books}

# Seed book authors (from seed_books.py)
SEED_AUTHORS = {
    "Cien Años de Soledad": "Gabriel García Márquez",
    "Rayuela": "Julio Cortázar",
    "Pedro Páramo": "Juan Rulfo",
    "La Casa de los Espíritus": "Isabel Allende",
    "El Túnel": "Ernesto Sabato",
    "Ficciones": "Jorge Luis Borges",
    "Como Agua para Chocolate": "Laura Esquivel",
    "El Amor en los Tiempos del Cólera": "Gabriel García Márquez",
    "La Sombra del Viento": "Carlos Ruiz Zafón",
    "Aura": "Carlos Fuentes",
    "Los Detectives Salvajes": "Roberto Bolaño",
    "Crónica de una Muerte Anunciada": "Gabriel García Márquez",
    "Don Quijote de la Mancha": "Miguel de Cervantes",
    "El Principito": "Antoine de Saint-Exupéry",
    "Orgullo y Prejuicio": "Jane Austen",
    "Crimen y Castigo": "Fiódor Dostoievski",
    "Los Miserables": "Victor Hugo",
    "La Odisea": "Homero",
    "Anna Karenina": "León Tolstói",
    "Hamlet": "William Shakespeare",
    "La Divina Comedia": "Dante Alighieri",
    "Madame Bovary": "Gustave Flaubert",
    "El Conde de Montecristo": "Alejandro Dumas",
    "Las Mil y Una Noches": "Anónimo",
    "1984": "George Orwell",
    "Un Mundo Feliz": "Aldous Huxley",
    "Fahrenheit 451": "Ray Bradbury",
    "Dune": "Frank Herbert",
    "Fundación": "Isaac Asimov",
    "Crónicas Marcianas": "Ray Bradbury",
    "Neuromante": "William Gibson",
    "El Juego de Ender": "Orson Scott Card",
    "2001: Una Odisea del Espacio": "Arthur C. Clarke",
    "Solaris": "Stanislaw Lem",
    "La Guerra de los Mundos": "H. G. Wells",
    "El Marciano": "Andy Weir",
    "It": "Stephen King",
    "Drácula": "Bram Stoker",
    "Frankenstein": "Mary Shelley",
    "El Resplandor": "Stephen King",
    "La Llamada de Cthulhu": "H. P. Lovecraft",
    "El Exorcista": "William Peter Blatty",
    "Cementerio de Animales": "Stephen King",
    "El Fantasma de la Ópera": "Gastón Leroux",
    "La Maldición de Hill House": "Shirley Jackson",
    "Misery": "Stephen King",
    "Veinte Poemas de Amor y una Canción Desesperada": "Pablo Neruda",
    "Canto General": "Pablo Neruda",
    "Poeta en Nueva York": "Federico García Lorca",
    "Romancero Gitano": "Federico García Lorca",
    "Altazor": "Vicente Huidobro",
    "Trilce": "César Vallejo",
    "Los Heraldos Negros": "César Vallejo",
    "Piedra de Sol": "Octavio Paz",
    "Hojas de Hierba": "Walt Whitman",
    "Cien Sonetos de Amor": "Pablo Neruda",
    "Sapiens: De Animales a Dioses": "Yuval Noah Harari",
    "El Arte de la Guerra": "Sun Tzu",
    "Breve Historia del Mundo": "Ernst H. Gombrich",
    "Los Conquistadores": "Matthew Restall",
    "El Diario de Ana Frank": "Ana Frank",
    "Memorias de Adriano": "Marguerite Yourcenar",
    "Historia de Dos Ciudades": "Charles Dickens",
    "21 Lecciones para el Siglo XXI": "Yuval Noah Harari",
    "Las Venas Abiertas de América Latina": "Eduardo Galeano",
    "El Laberinto de la Soledad": "Octavio Paz",
    "El Mundo de Sofía": "Jostein Gaarder",
    "Así Habló Zaratustra": "Friedrich Nietzsche",
    "La República": "Platón",
    "Meditaciones": "Marco Aurelio",
    "El Banquete": "Platón",
    "El Ser y la Nada": "Jean-Paul Sartre",
    "El Arte de Amar": "Erich Fromm",
    "Ética para Amador": "Fernando Savater",
    "Elogio de la Locura": "Erasmo de Rotterdam",
    "El Príncipe": "Nicolás Maquiavelo",
    "El Alquimista": "Paulo Coelho",
    "Los 7 Hábitos de la Gente Altamente Efectiva": "Stephen Covey",
    "El Poder del Ahora": "Eckhart Tolle",
    "Padre Rico, Padre Pobre": "Robert Kiyosaki",
    "Hábitos Atómicos": "James Clear",
    "El Monje que Vendió su Ferrari": "Robin Sharma",
    "Piense y Hágase Rico": "Napoleon Hill",
    "El Sutil Arte de que No te Importe Nada": "Mark Manson",
    "Los Cuatro Acuerdos": "Miguel Ruiz",
    "Inteligencia Emocional": "Daniel Goleman",
    "Romeo y Julieta": "William Shakespeare",
    "Cumbres Borrascosas": "Emily Brontë",
    "Jane Eyre": "Charlotte Brontë",
    "El Fantasma de Canterville": "Oscar Wilde",
    "Persuasión": "Jane Austen",
    "Las Batallas en el Desierto": "José Emilio Pacheco",
    "Doctor Zhivago": "Boris Pasternak",
    "La Dama de las Camelias": "Alejandro Dumas (hijo)",
    "Corazón": "Edmundo de Amicis",
    "La Isla del Tesoro": "Robert Louis Stevenson",
    "Veinte Mil Leguas de Viaje Submarino": "Julio Verne",
    "El Señor de los Anillos": "J. R. R. Tolkien",
    "El Hobbit": "J. R. R. Tolkien",
    "Las Aventuras de Tom Sawyer": "Mark Twain",
    "Robinson Crusoe": "Daniel Defoe",
    "La Vuelta al Mundo en 80 Días": "Julio Verne",
    "Moby Dick": "Herman Melville",
    "Los Tres Mosqueteros": "Alejandro Dumas",
    "Viaje al Centro de la Tierra": "Julio Verne",
    "Cosmos": "Carl Sagan",
    "Breve Historia del Tiempo": "Stephen Hawking",
    "El Gen Egoísta": "Richard Dawkins",
    "El Universo en una Cáscara de Nuez": "Stephen Hawking",
    "Astrofísica para Gente con Prisa": "Neil deGrasse Tyson",
    "El Origen de las Especies": "Charles Darwin",
    "La Estructura de las Revoluciones Científicas": "Thomas Kuhn",
    "La Doble Hélice": "James Watson",
    "Seis Piezas Fáciles": "Richard Feynman",
    "Un Punto Azul Pálido": "Carl Sagan",
    "Charlie y la Fábrica de Chocolate": "Roald Dahl",
    "Matilda": "Roald Dahl",
    "Las Crónicas de Narnia: El León, la Bruja y el Ropero": "C. S. Lewis",
    "Harry Potter y la Piedra Filosofal": "J. K. Rowling",
    "El Diario de Greg": "Jeff Kinney",
    "James y el Melocotón Gigante": "Roald Dahl",
    "Donde Viven los Monstruos": "Maurice Sendak",
    "Alicia en el País de las Maravillas": "Lewis Carroll",
    "Cuentos de la Selva": "Horacio Quiroga",
}

# Known authors for books NOT in seed (added later via imports)
KNOWN_AUTHORS = {
    "Rayuelas mentales": "Rayuela (fan project)",
    "Anaconda y otros cuentos": "Horacio Quiroga",
    "César o nada": "Pío Baroja",
    "El Caballero Carmelo": "Abraham Valdelomar",
    "El Mundo Es Ancho Y Ajeno": "Ciro Alegría",
    "El Guardavía de Charles Dickens en PDF": "Charles Dickens",
    "El Idiota": "Fiódor Dostoievski",
    "Los Papeles Póstumos del Club Pickwick de Charles Dickens en PDF": "Charles Dickens",
    "Las Aventuras del Capitán Hatteras": "Julio Verne",
    "A buen fin no hay mal principio": "Pío Baroja",
    "Un Árbol de Navidad y Una Boda": "Charles Dickens",
    "La Casa Encantada de Charles Dickens en PDF": "Charles Dickens",
    "La Estrella del Sur": "Julio Verne",
    "La Caza del Meteoro": "Julio Verne",
    "Aventuras de Tres Rusos y Tres Ingleses en el África Austral": "Julio Verne",
    "El Faro del Fin del Mundo": "Julio Verne",
    "Romeo y Julieta": "William Shakespeare",
    "Memorias de subsuelo": "Fiódor Dostoievski",
    "Divina comedia": "Dante Alighieri",
    "Los heraldos negros": "César Vallejo",
    "La Odisea": "Homero",
    "Crimen y castigo": "Fiódor Dostoievski",
    "Edipo rey": "Sófocles",
    "Sangre de Campeón: Sin Cadenas": "Juan José Arreola",
    "La Condena": "Franz Kafka",
    "El Castillo": "Franz Kafka",
    "Relatos Cortos": "Franz Kafka",
    "Un Artista del Hambre": "Franz Kafka",
    "Carta al Padre": "Franz Kafka",
    "Informe para una Academia": "Franz Kafka",
    "Un Médico Rural": "Franz Kafka",
    "En la Colonia Penitenciaria": "Franz Kafka",
    "El Proceso": "Franz Kafka",
    "Las Preocupaciones de un Padre de Familia": "Franz Kafka",
    "El Fogonero": "Franz Kafka",
    "Josefina la Cantora o El Pueblo de los Ratones": "Franz Kafka",
    "El Sueño del Príncipe": "Franz Kafka",
    "El Adolescente": "Fiódor Dostoievski",
    "El Jugador": "Fiódor Dostoievski",
    "Los Endemoniados": "Fiódor Dostoievski",
    "El Gran Inquisidor": "Fiódor Dostoievski",
    "Los Hermanos Karamázov": "Fiódor Dostoievski",
    "Humillados y Ofendidos": "Fiódor Dostoievski",
    "Nétochka Nezvánova": "Fiódor Dostoievski",
    "Diario de un Escritor": "Fiódor Dostoievski",
    "El Cocodrilo": "Fiódor Dostoievski",
    "El Pueblo Aéreo": "Fiódor Dostoievski",
    "La Jornada de un Periodista Americano en el Año 2889": "Julio Verne",
    "César Cascabel": "Julio Verne",
    "Dueño del Mundo": "Julio Verne",
    "El Chancellor": "Julio Verne",
    "Norte Contra Sur": "Julio Verne",
    "El Doctor Ox": "Julio Verne",
    "Los Hijos del Capitán Grant": "Julio Verne",
    "El Archipiélago en Llamas": "Julio Verne",
    "Las Indias Negras": "Julio Verne",
    "Un Drama en Livonia": "Julio Verne",
    "La Invasión del Mar": "Julio Verne",
    "El Soberbio Orinoco": "Julio Verne",
    "El País de las Pieles": "Julio Verne",
    "Robur el Conquistador": "Julio Verne",
    "El Testamento de un Excéntrico": "Julio Verne",
    "Matías Sandorf": "Julio Verne",
    "La Isla de Hélice": "Julio Verne",
    "Escuela de Robinsones": "Julio Verne",
    "El Piloto del Danubio": "Julio Verne",
    "Alrededor de la Luna": "Julio Verne",
    "Claudio Bombarnac": "Julio Verne",
    "La Isla Misteriosa": "Julio Verne",
    "La Agencia Thompson y Cía.": "Julio Verne",
    "Una Ciudad Flotante": "Julio Verne",
    "El Castillo de los Cárpatos": "Julio Verne",
    "Barnaby Rudge de Charles Dickens en PDF": "Charles Dickens",
    "Grandes Esperanzas de Charles Dickens en PDF": "Charles Dickens",
    "El Misterio de Edwin Drood de Charles Dickens en PDF": "Charles Dickens",
    "El Manuscrito de un Loco de Charles Dickens en PDF": "Charles Dickens",
    "Tiempos Difíciles de Charles Dickens en PDF": "Charles Dickens",
    "Historias de Fantasmas de Charles Dickens en PDF": "Charles Dickens",
    "La Historia de Nadie de Charles Dickens en PDF": "Charles Dickens",
    "Cuento de Navidad de Charles Dickens en PDF": "Charles Dickens",
    "Una Casa en Alquiler de Charles Dickens en PDF": "Charles Dickens",
    "Historia de Dos Ciudades de Charles Dickens en PDF": "Charles Dickens",
    "Contemplación": "Fiódor Dostoievski",
    "La Metamorfosis": "Franz Kafka",
    "Ante la Ley": "Franz Kafka",
    "El Sueño de un Hombre Ridículo": "Fiódor Dostoievski",
    "La Sumisa": "Franz Kafka",
    "La Patrona": "Franz Kafka",
    "El Secreto de Wilhelm Storitz": "Julio Verne",
    "De la Tierra a la Luna": "Julio Verne",
    "Familia sin Nombre": "Julio Verne",
    "La Vuelta al Mundo en Ochenta Días": "Julio Verne",
    "Cinco Semanas en Globo": "Julio Verne",
}

# Local PDFs available
LOCAL_PDFS = {
    "Anaconda y otros cuentos": "Anaconda y otros cuentos - Horacio Quiroga.pdf",
    "César o nada": "cesaronadanovela00baro.pdf",
    "El Hijo": "El Hijo - Horacio Quiroga.pdf",
    "El Mayorazgo de Labra": "elmayorazgodela00barogoog.pdf",
}

# Classify each production book
print("=" * 120)
print("INVENTARIO COMPLETO DE PORTADAS - AETERNUMLIBRARY")
print("=" * 120)
print("")

# Separate into categories
genéricos = []
locales = []

for b in sorted(prod_books, key=lambda x: x['id']):
    bid = b['id']
    title = (b.get('title') or '').strip()
    cover = b.get('cover_image_url') or ''
    
    # Get author
    author = KNOWN_AUTHORS.get(title) or SEED_AUTHORS.get(title) or "DESCONOCIDO"
    
    # Has local PDF?
    has_pdf = title in LOCAL_PDFS
    
    if 'unsplash' in cover:
        genéricos.append((bid, title, author, has_pdf))
    else:
        locales.append((bid, title, author, cover, has_pdf))

print("RESUMEN:")
print("  Total publicados: %d" % len(prod_books))
print("  Portada local (subida): %d" % len(locales))
print("  Portada generica (Unsplash): %d" % len(genéricos))
print("")

print("=" * 120)
print("SECCION A: PORTADAS LOCALES (28 libros) - Requieren verificacion de calidad")
print("=" * 120)
print("")
print("  %-4s | %-55s | %-30s | %-8s | %s" % ("ID", "TITULO", "AUTOR", "PDF?", "ESTADO"))
print("  " + "-" * 4 + "-+-" + "-" * 55 + "-+-" + "-" * 30 + "-+-" + "-" * 8 + "-+-" + "-" * 20)

for bid, title, author, cover, has_pdf in locales:
    fname = cover.split('/')[-1] if cover else ''
    # Determine if likely a real cover
    if fname.startswith('imagen_') or '_imagen_' in fname:
        status = "Portada PDF (upload)"
    elif fname.endswith('.jpg') and len(fname) == 39:  # hash-based name
        status = "Portada importada"
    else:
        status = "Portada subida"
    pdf_str = "SI" if has_pdf else ""
    print("  %-4d | %-55s | %-30s | %-8s | %s" % (bid, title[:55], author[:30], pdf_str, status))

print("")
print("=" * 120)
print("SECCION B: PORTADAS GENERICAS UNSPLASH (65 libros) - TODOS necesitan portada real")
print("=" * 120)
print("")
print("  %-4s | %-55s | %-30s | %-8s | %-15s | %s" % ("ID", "TITULO", "AUTOR", "PDF?", "FUENTE", "OBSERVACIONES"))
print("  " + "-" * 4 + "-+-" + "-" * 55 + "-+-" + "-" * 30 + "-+-" + "-" * 8 + "-+-" + "-" * 15 + "-+-" + "-" * 30)

for bid, title, author, has_pdf in genéricos:
    pdf_str = "SI" if has_pdf else ""
    if has_pdf:
        source = "PDF local"
        obs = "Extraer portada del PDF"
    elif author in ("Franz Kafka", "Fiódor Dostoievski", "Julio Verne", "Charles Dickens"):
        source = "Internet Archive"
        obs = "Clasico de dominio publico"
    elif "Dickens en PDF" in title:
        source = "Internet Archive"
        obs = "Dickens - dominio publico"
    elif author in ("César Vallejo", "Pablo Neruda", "Octavio Paz", "Federico García Lorca"):
        source = "Wikimedia"
        obs = "Poeta hispanoamericano"
    else:
        source = "Open Library"
        obs = ""
    print("  %-4d | %-55s | %-30s | %-8s | %-15s | %s" % (bid, title[:55], author[:30], pdf_str, source, obs))

print("")
print("=" * 120)
print("SECCION C: LIBROS CON PDF LOCAL DISPONIBLE")
print("=" * 120)
print("")
for title, pdf_name in sorted(LOCAL_PDFS.items()):
    print("  %s -> %s" % (title, pdf_name))
print("")
print("NOTA: 'El Hijo' (Horacio Quiroga) y 'El Mayorazgo de Labra' (Pio Baroja)")
print("tienen PDF local pero NO aparecen en los 93 libros publicados actuales.")
print("Solo 'Anaconda' y 'Cesar o nada' estan publicados.")

print("")
print("=" * 120)
print("SECCION D: RESUMEN POR AUTOR (libros con portada generica)")
print("=" * 120)
print("")

from collections import Counter
author_counts = Counter()
for bid, title, author, has_pdf in genéricos:
    author_counts[author] += 1

for author, count in author_counts.most_common():
    print("  %-35s: %d libros" % (author, count))
