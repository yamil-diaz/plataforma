# INFORME TABLA DEFINITIVA - AeternumLibrary

## Estado de Produccion

| Campo | Valor |
|-------|-------|
| Total libros | 164 |
| Produccion modificada | NO |
| Modo | SOLO LECTURA |
| Fuente | diag_result.json + auditoria produccion |

## Resumen de Decisiones

| Decision | Cantidad | % |
|----------|----------|---|
| CONSERVAR | 16 | 9.8% |
| ELIMINAR_DUPLICADO | 17 | 10.4% |
| REPROCESAR_DESDE_CONTENIDO | 112 | 68.3% |
| REPROCESAR_DESDE_PDF | 1 | 0.6% |
| REVISAR_MANUALMENTE | 18 | 11.0% |

## Tabla Definitiva

| ID | Titulo | Autor | Decision | Grupo Dup | Superior | PDF | Problema | Justificacion |
|----|--------|-------|----------|-----------|----------|-----|----------|---------------|
| 1 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 2 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 3 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 4 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 5 | Cien Anos de Soledad | Gabriel Garcia Marquez | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 6 | Rayuela | Julio Cortazar | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 7 | Pedro Paramo | Juan Rulfo | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 8 | La Casa de los Espiritus | Isabel Allende | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 9 | El Tunel | Ernesto Sabato | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 10 | Ficciones | Jorge Luis Borges | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 11 | Como Agua para Chocolate | Laura Esquivel | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 12 | El Amor en los Tiempos del Colera | Gabriel Garcia Marquez | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 13 | La Sombra del Viento | Carlos Ruiz Zafon | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 14 | Aura | Carlos Fuentes | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 15 | Los Detectives Salvajes | Roberto Bolano | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 16 | Cronica de una Muerte Anunciada | Gabriel Garcia Marquez | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 17 | Don Quijote de la Mancha | Miguel de Cervantes | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 18 | El Principito | Antoine de Saint-Exupery | REPROCESAR_DESDE_CONTENIDO | [18, 128] | - | NO | FAB+DUP | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 19 | Orgullo y Prejuicio | Jane Austen | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 20 | Crimen y Castigo | Fiodor Dostoievski | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 21 | Los Miserables | Victor Hugo | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 22 | La Odisea | Homero | REPROCESAR_DESDE_CONTENIDO | [22, 144, 157, 170] | - | NO | FAB+DUP | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 23 | Anna Karenina | Leon Tolstoi | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 24 | Hamlet | William Shakespeare | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 25 | La Divina Comedia | Dante Alighieri | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 26 | Madame Bovary | Gustave Flaubert | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 27 | El Conde de Montecristo | Alejandro Dumas | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 28 | Las Mil y Una Noches | Anonimo | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 29 | 1984 | George Orwell | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 30 | Un Mundo Feliz | Aldous Huxley | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 31 | Fahrenheit 451 | Ray Bradbury | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 32 | Dune | Frank Herbert | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 33 | Fundacion | Isaac Asimov | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 34 | Cronicas Marcianas | Ray Bradbury | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 35 | Neuromante | William Gibson | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 36 | El Juego de Ender | Orson Scott Card | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 37 | 2001: Una Odisea del Espacio | Arthur C. Clarke | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 38 | Solaris | Stanislaw Lem | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 39 | La Guerra de los Mundos | H. G. Wells | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 40 | El Marciano | Andy Weir | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 41 | It | Stephen King | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 42 | Dracula | Bram Stoker | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 43 | Frankenstein | Mary Shelley | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 44 | El Resplandor | Stephen King | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 45 | La Llamada de Cthulhu | H. P. Lovecraft | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 46 | El Exorcista | William Peter Blatty | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 47 | Cementerio de Animales | Stephen King | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 48 | El Fantasma de la Opera | Gaston Leroux | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 49 | La Maldicion de Hill House | Shirley Jackson | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 50 | Misery | Stephen King | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 51 | Veinte Poemas de Amor y una Cancion Dese | Pablo Neruda | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 52 | Canto General | Pablo Neruda | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 53 | Poeta en Nueva York | Federico Garcia Lorca | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 54 | Romancero Gitano | Federico Garcia Lorca | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 55 | Altazor | Vicente Huidobro | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 56 | Trilce | Cesar Vallejo | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 57 | Los Heraldos Negros | Cesar Vallejo | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 58 | Piedra de Sol | Octavio Paz | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 59 | Hojas de Hierba | Walt Whitman | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 60 | Cien Sonetos de Amor | Pablo Neruda | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 61 | Sapiens: De Animales a Dioses | Yuval Noah Harari | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 62 | El Arte de la Guerra | Sun Tzu | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 63 | Breve Historia del Mundo | Ernst H. Gombrich | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 64 | Los Conquistadores | John Hemming | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 65 | El Diario de Ana Frank | Ana Frank | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 66 | Memorias de Adriano | Marguerite Yourcenar | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 67 | Historia de Dos Ciudades | Charles Dickens | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 68 | 21 Lecciones para el Siglo XXI | Yuval Noah Harari | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 69 | Las Venas Abiertas de America Latina | Eduardo Galeano | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 70 | El Laberinto de la Soledad | Octavio Paz | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 71 | El Mundo de Sofia | Jostein Gaarder | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 72 | Asi Hablo Zaratustra | Friedrich Nietzsche | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 73 | La Republica | Platon | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 74 | Meditaciones | Marco Aurelio | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 75 | El Banquete | Platon | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 76 | El Ser y la Nada | Jean-Paul Sartre | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 77 | El Arte de Amar | Erich Fromm | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 78 | Etica para Amador | Fernando Savater | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 79 | Elogio de la Locura | Erasmo de Rotterdam | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 80 | El Principe | Maquiavelo | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 81 | El Alquimista | Paulo Coelho | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 82 | Los 7 Habitos de la Gente Altamente Efec | Stephen Covey | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 83 | El Poder del Ahora | Eckhart Tolle | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 84 | Padre Rico, Padre Pobre | Robert Kiyosaki | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 85 | Habitos Atomicos | James Clear | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 86 | El Monje que Vendio su Ferrari | Robin Sharma | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 87 | Piense y Hagase Rico | Napoleon Hill | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 88 | El Sutil Arte de que No te Importe Nada | Mark Manson | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 89 | Los Cuatro Acuerdos | Don Miguel Ruiz | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 90 | Inteligencia Emocional | Daniel Goleman | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 91 | Romeo y Julieta | William Shakespeare | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 92 | Cumbres Borrascosas | Emily Bronte | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 93 | Jane Eyre | Charlotte Bronte | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 94 | El Fantasma de Canterville | Oscar Wilde | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 95 | Persuasion | Jane Austen | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 96 | Las Batallas en el Desierto | Jose Emilio Pacheco | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 97 | Doctor Zhivago | Boris Pasternak | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 98 | La Dama de las Camelias | Alexandre Dumas | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 99 | El Amor en los Tiempos de la Peste | Gabriel Garcia Marquez | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 100 | Corazon | Edmondo De Amicis | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 101 | La Isla del Tesoro | Robert Louis Stevenson | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 102 | Veinte Mil Leguas de Viaje Submarino | Julio Verne | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 103 | El Senor de los Anillos | J. R. R. Tolkien | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 104 | El Hobbit | J. R. R. Tolkien | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 105 | Las Aventuras de Tom Sawyer | Mark Twain | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 106 | Robinson Crusoe | Daniel Defoe | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 107 | La Vuelta al Mundo en 80 Dias | Julio Verne | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 108 | Moby Dick | Herman Melville | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 109 | Los Tres Mosqueteros | Alexandre Dumas | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 110 | Viaje al Centro de la Tierra | Julio Verne | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 111 | Cosmos | Carl Sagan | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 112 | Breve Historia del Tiempo | Stephen Hawking | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 113 | El Gen Egoista | Richard Dawkins | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 114 | El Universo en una Cascara de Nuez | Stephen Hawking | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 115 | Astrofisica para Gente con Prisa | Neil deGrasse Tyson | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 116 | El Origen de las Especies | Charles Darwin | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 117 | La Estructura de las Revoluciones Cienti | Thomas Kuhn | CONSERVAR | - | - | NO | FAB | Contenido original verificable en seed_books.py; protegido por auditoria |
| 118 | La Doble Helice | James Watson | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 119 | Seis Piezas Faciles | Richard Feynman | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 120 | Un Punto Azul Palido | Carl Sagan | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 121 | Charlie y la Fabrica de Chocolate | Roald Dahl | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 122 | Matilda | Roald Dahl | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 123 | Las Cronicas de Narnia: El Leon, la Bruj | C. S. Lewis | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 124 | Harry Potter y la Piedra Filosofal | J. K. Rowling | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 125 | El Diario de Greg | Jeff Kinney | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 126 | James y el Melocoton Gigante | Roald Dahl | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 127 | Donde Viven los Monstruos | Maurice Sendak | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 128 | El Principito | Antoine de Saint-Exupery | REPROCESAR_DESDE_CONTENIDO | [18, 128] | - | NO | FAB+DUP | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 129 | Alicia en el Pais de las Maravillas | Lewis Carroll | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 130 | Cuentos de la Selva | Horacio Quiroga | REPROCESAR_DESDE_CONTENIDO | - | - | NO | FAB | Seed con contenido multiplicado 200x; fuente original en seed_books.py |
| 131 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 132 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 133 | Crimen y castigo | S/D | REVISAR_MANUALMENTE | [133, 159] | 133 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 134 | Los heraldos negros | S/D | REVISAR_MANUALMENTE | [134, 147, 160] | 134 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 135 | Sangre de Campe¾n: Sin Cadenas | S/D | REVISAR_MANUALMENTE | [135, 148, 161] | 135 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 136 | Ciro Alegria   El Mundo Es Ancho Y Ajeno | S/D | REVISAR_MANUALMENTE | [136, 149, 162] | 136 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 137 | CrimenCastigo.PDF | S/D | REVISAR_MANUALMENTE | [137, 150, 163] | 137 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 138 | Microsoft Word - Dante Alighieri - Divin | S/D | REVISAR_MANUALMENTE | [138, 151, 164] | 138 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 139 | El Caballero Carmelo | S/D | REVISAR_MANUALMENTE | [139, 152, 165] | 139 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 140 | EL MUNDO ES ANCHO Y AJENO | S/D | REVISAR_MANUALMENTE | [140, 153, 166] | 140 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 141 | edipo.PDF | S/D | REVISAR_MANUALMENTE | [141, 154, 167] | 141 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 142 | Romeo y Julieta | S/D | REVISAR_MANUALMENTE | [142, 155, 168] | 142 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 143 | ÐA CATITA | S/D | REVISAR_MANUALMENTE | [143, 156, 169] | 143 | NO | PH+DUP | Placeholder pero es copia superior del grupo; verificar si existe fuente alternativa |
| 144 | La Odisea | S/D | ELIMINAR_DUPLICADO | [22, 144, 157, 170] | 22 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 22 |
| 145 | Memorias de subsuelo  | S/D | CONSERVAR | - | - | NO | FAB | Contenido completo y confiable; protegido por auditoria |
| 146 | Sin datos en snapshot | Desconocido | REVISAR_MANUALMENTE | - | - | NO | - | Sin datos suficientes en snapshot; requiere verificacion manual |
| 147 | Los heraldos negros | S/D | ELIMINAR_DUPLICADO | [134, 147, 160] | 134 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 134 |
| 148 | Sangre de Campe¾n: Sin Cadenas | S/D | ELIMINAR_DUPLICADO | [135, 148, 161] | 135 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 135 |
| 149 | Ciro Alegria   El Mundo Es Ancho Y Ajeno | S/D | ELIMINAR_DUPLICADO | [136, 149, 162] | 136 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 136 |
| 150 | CrimenCastigo.PDF | S/D | ELIMINAR_DUPLICADO | [137, 150, 163] | 137 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 137 |
| 151 | Microsoft Word - Dante Alighieri - Divin | S/D | ELIMINAR_DUPLICADO | [138, 151, 164] | 138 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 138 |
| 152 | El Caballero Carmelo | S/D | ELIMINAR_DUPLICADO | [139, 152, 165] | 139 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 139 |
| 153 | EL MUNDO ES ANCHO Y AJENO | S/D | ELIMINAR_DUPLICADO | [140, 153, 166] | 140 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 140 |
| 154 | edipo.PDF | S/D | ELIMINAR_DUPLICADO | [141, 154, 167] | 141 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 141 |
| 155 | Romeo y Julieta | S/D | ELIMINAR_DUPLICADO | [142, 155, 168] | 142 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 142 |
| 156 | ÐA CATITA | S/D | ELIMINAR_DUPLICADO | [143, 156, 169] | 143 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 143 |
| 157 | La Odisea | S/D | ELIMINAR_DUPLICADO | [22, 144, 157, 170] | 22 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 22 |
| 158 | Noches blancas  | S/D | CONSERVAR | - | - | NO | FAB | Contenido completo y confiable; protegido por auditoria |
| 159 | Crimen y castigo | S/D | ELIMINAR_DUPLICADO | [133, 159] | 133 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 133 |
| 160 | Los heraldos negros | S/D | ELIMINAR_DUPLICADO | [134, 147, 160] | 134 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 134 |
| 161 | Sangre de Campe¾n: Sin Cadenas | S/D | ELIMINAR_DUPLICADO | [135, 148, 161] | 135 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 135 |
| 162 | Ciro Alegria   El Mundo Es Ancho Y Ajeno | S/D | ELIMINAR_DUPLICADO | [136, 149, 162] | 136 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 136 |
| 163 | CrimenCastigo.PDF | S/D | ELIMINAR_DUPLICADO | [137, 150, 163] | 137 | NO | PH+DUP | Placeholder y duplicado inferior; copia superior: ID 137 |
| 175 | Rayuelas mentales | Autor desconocido | REPROCESAR_DESDE_PDF | - | - | SI | - | Existe fuente PDF fisica valida (1,364,423 bytes); reconstruir contenido y paginacion desde PDF |

## Grupos de Duplicados

### ANA CATITA
- IDs: [143, 156, 169]
- Copia superior: 143

### Ciro Alegria   El Mundo Es Ancho Y Ajeno
- IDs: [136, 149, 162]
- Copia superior: 136

### Crimen y castigo
- IDs: [133, 159]
- Copia superior: 133

### CrimenCastigo.PDF
- IDs: [137, 150, 163]
- Copia superior: 137

### EL MUNDO ES ANCHO Y AJENO
- IDs: [140, 153, 166]
- Copia superior: 140

### El Caballero Carmelo
- IDs: [139, 152, 165]
- Copia superior: 139

### El Principito
- IDs: [18, 128]
- Copia superior: 18

### La Odisea
- IDs: [22, 144, 157, 170]
- Copia superior: 22

### Los heraldos negros
- IDs: [134, 147, 160]
- Copia superior: 134

### Microsoft Word - Dante Alighieri - Divina comedia.doc
- IDs: [138, 151, 164]
- Copia superior: 138

### Romeo y Julieta
- IDs: [142, 155, 168]
- Copia superior: 142

### Sangre de Campeon: Sin Cadenas
- IDs: [135, 148, 161]
- Copia superior: 135

### edipo.PDF
- IDs: [141, 154, 167]
- Copia superior: 141

## CONSERVAR (16)

- **ID 5** — Cien Anos de Soledad | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 6** — Rayuela | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 7** — Pedro Paramo | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 8** — La Casa de los Espiritus | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 10** — Ficciones | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 11** — Como Agua para Chocolate | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 12** — El Amor en los Tiempos del Colera | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 13** — La Sombra del Viento | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 19** — Orgullo y Prejuicio | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 21** — Los Miserables | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 29** — 1984 | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 34** — Cronicas Marcianas | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 41** — It | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 117** — La Estructura de las Revoluciones Cientificas | Contenido original verificable en seed_books.py; protegido por auditoria
- **ID 145** — Memorias de subsuelo  | Contenido completo y confiable; protegido por auditoria
- **ID 158** — Noches blancas  | Contenido completo y confiable; protegido por auditoria

## ELIMINAR_DUPLICADO (17)

- **ID 144** — La Odisea | Placeholder y duplicado inferior; copia superior: ID 22
- **ID 147** — Los heraldos negros | Placeholder y duplicado inferior; copia superior: ID 134
- **ID 148** — Sangre de Campe¾n: Sin Cadenas | Placeholder y duplicado inferior; copia superior: ID 135
- **ID 149** — Ciro Alegria   El Mundo Es Ancho Y Ajeno | Placeholder y duplicado inferior; copia superior: ID 136
- **ID 150** — CrimenCastigo.PDF | Placeholder y duplicado inferior; copia superior: ID 137
- **ID 151** — Microsoft Word - Dante Alighieri - Divina comedia.doc | Placeholder y duplicado inferior; copia superior: ID 138
- **ID 152** — El Caballero Carmelo | Placeholder y duplicado inferior; copia superior: ID 139
- **ID 153** — EL MUNDO ES ANCHO Y AJENO | Placeholder y duplicado inferior; copia superior: ID 140
- **ID 154** — edipo.PDF | Placeholder y duplicado inferior; copia superior: ID 141
- **ID 155** — Romeo y Julieta | Placeholder y duplicado inferior; copia superior: ID 142
- **ID 156** — ÐA CATITA | Placeholder y duplicado inferior; copia superior: ID 143
- **ID 157** — La Odisea | Placeholder y duplicado inferior; copia superior: ID 22
- **ID 159** — Crimen y castigo | Placeholder y duplicado inferior; copia superior: ID 133
- **ID 160** — Los heraldos negros | Placeholder y duplicado inferior; copia superior: ID 134
- **ID 161** — Sangre de Campe¾n: Sin Cadenas | Placeholder y duplicado inferior; copia superior: ID 135
- **ID 162** — Ciro Alegria   El Mundo Es Ancho Y Ajeno | Placeholder y duplicado inferior; copia superior: ID 136
- **ID 163** — CrimenCastigo.PDF | Placeholder y duplicado inferior; copia superior: ID 137

## REPROCESAR_DESDE_PDF (1)

- **ID 175** — Rayuelas mentales | Existe fuente PDF fisica valida (1,364,423 bytes); reconstruir contenido y pagin

## REPROCESAR_DESDE_CONTENIDO (112)

- **ID 9** — El Tunel | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 14** — Aura | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 15** — Los Detectives Salvajes | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 16** — Cronica de una Muerte Anunciada | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 17** — Don Quijote de la Mancha | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 18** — El Principito | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 20** — Crimen y Castigo | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 22** — La Odisea | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 23** — Anna Karenina | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 24** — Hamlet | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 25** — La Divina Comedia | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 26** — Madame Bovary | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 27** — El Conde de Montecristo | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 28** — Las Mil y Una Noches | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 30** — Un Mundo Feliz | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 31** — Fahrenheit 451 | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 32** — Dune | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 33** — Fundacion | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 35** — Neuromante | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 36** — El Juego de Ender | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 37** — 2001: Una Odisea del Espacio | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 38** — Solaris | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 39** — La Guerra de los Mundos | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 40** — El Marciano | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 42** — Dracula | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 43** — Frankenstein | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 44** — El Resplandor | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 45** — La Llamada de Cthulhu | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 46** — El Exorcista | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 47** — Cementerio de Animales | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 48** — El Fantasma de la Opera | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 49** — La Maldicion de Hill House | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 50** — Misery | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 51** — Veinte Poemas de Amor y una Cancion Desesperada | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 52** — Canto General | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 53** — Poeta en Nueva York | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 54** — Romancero Gitano | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 55** — Altazor | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 56** — Trilce | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 57** — Los Heraldos Negros | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 58** — Piedra de Sol | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 59** — Hojas de Hierba | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 60** — Cien Sonetos de Amor | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 61** — Sapiens: De Animales a Dioses | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 62** — El Arte de la Guerra | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 63** — Breve Historia del Mundo | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 64** — Los Conquistadores | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 65** — El Diario de Ana Frank | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 66** — Memorias de Adriano | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 67** — Historia de Dos Ciudades | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 68** — 21 Lecciones para el Siglo XXI | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 69** — Las Venas Abiertas de America Latina | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 70** — El Laberinto de la Soledad | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 71** — El Mundo de Sofia | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 72** — Asi Hablo Zaratustra | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 73** — La Republica | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 74** — Meditaciones | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 75** — El Banquete | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 76** — El Ser y la Nada | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 77** — El Arte de Amar | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 78** — Etica para Amador | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 79** — Elogio de la Locura | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 80** — El Principe | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 81** — El Alquimista | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 82** — Los 7 Habitos de la Gente Altamente Efectiva | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 83** — El Poder del Ahora | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 84** — Padre Rico, Padre Pobre | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 85** — Habitos Atomicos | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 86** — El Monje que Vendio su Ferrari | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 87** — Piense y Hagase Rico | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 88** — El Sutil Arte de que No te Importe Nada | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 89** — Los Cuatro Acuerdos | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 90** — Inteligencia Emocional | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 91** — Romeo y Julieta | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 92** — Cumbres Borrascosas | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 93** — Jane Eyre | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 94** — El Fantasma de Canterville | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 95** — Persuasion | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 96** — Las Batallas en el Desierto | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 97** — Doctor Zhivago | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 98** — La Dama de las Camelias | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 99** — El Amor en los Tiempos de la Peste | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 100** — Corazon | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 101** — La Isla del Tesoro | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 102** — Veinte Mil Leguas de Viaje Submarino | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 103** — El Senor de los Anillos | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 104** — El Hobbit | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 105** — Las Aventuras de Tom Sawyer | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 106** — Robinson Crusoe | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 107** — La Vuelta al Mundo en 80 Dias | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 108** — Moby Dick | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 109** — Los Tres Mosqueteros | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 110** — Viaje al Centro de la Tierra | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 111** — Cosmos | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 112** — Breve Historia del Tiempo | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 113** — El Gen Egoista | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 114** — El Universo en una Cascara de Nuez | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 115** — Astrofisica para Gente con Prisa | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 116** — El Origen de las Especies | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 118** — La Doble Helice | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 119** — Seis Piezas Faciles | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 120** — Un Punto Azul Palido | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 121** — Charlie y la Fabrica de Chocolate | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 122** — Matilda | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 123** — Las Cronicas de Narnia: El Leon, la Bruja y el Ropero | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 124** — Harry Potter y la Piedra Filosofal | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 125** — El Diario de Greg | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 126** — James y el Melocoton Gigante | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 127** — Donde Viven los Monstruos | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 128** — El Principito | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 129** — Alicia en el Pais de las Maravillas | Seed con contenido multiplicado 200x; fuente original en seed_books.py
- **ID 130** — Cuentos de la Selva | Seed con contenido multiplicado 200x; fuente original en seed_books.py

## REVISAR_MANUALMENTE (18)

- **ID 1** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual
- **ID 2** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual
- **ID 3** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual
- **ID 4** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual
- **ID 131** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual
- **ID 132** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual
- **ID 133** — Crimen y castigo | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 134** — Los heraldos negros | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 135** — Sangre de Campe¾n: Sin Cadenas | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 136** — Ciro Alegria   El Mundo Es Ancho Y Ajeno | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 137** — CrimenCastigo.PDF | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 138** — Microsoft Word - Dante Alighieri - Divina comedia.doc | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 139** — El Caballero Carmelo | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 140** — EL MUNDO ES ANCHO Y AJENO | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 141** — edipo.PDF | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 142** — Romeo y Julieta | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 143** — ÐA CATITA | Placeholder pero es copia superior del grupo; verificar si existe fuente alterna
- **ID 146** — Sin datos en snapshot | Sin datos suficientes en snapshot; requiere verificacion manual

## Validaciones Obligatorias

- Cada ID aparece exactamente una vez: **VERIFICADO**
- No existen IDs duplicados: **VERIFICADO**
- No falta ningun libro (total 164): **VERIFICADO**
- Suma de categorias coincide con total: **VERIFICADO**
- ID 175 aparece como REPROCESAR_DESDE_PDF: **VERIFICADO**
- Libros protegidos aparecen como CONSERVAR: **VERIFICADO**
- Ninguna operacion de escritura ejecutada: **VERIFICADO**

---

PRODUCCION NO FUE MODIFICADA.