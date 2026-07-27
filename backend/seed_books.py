"""
Script para insertar 120 libros de ejemplo organizados por categorías
en la base de datos PostgreSQL de producción.

Uso:
  DATABASE_URL="postgresql://..." python seed_books.py
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Portadas por categoría (imágenes de Unsplash gratuitas) ─────────────────
COVERS = {
    "Ficción": [
        "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400",
        "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400",
        "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
        "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400",
    ],
    "Clásicos": [
        "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400",
        "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400",
        "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=400",
        "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400",
    ],
    "Ciencia Ficción": [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400",
        "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=400",
        "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=400",
        "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=400",
    ],
    "Terror": [
        "https://images.unsplash.com/photo-1509248961895-40b907571b87?w=400",
        "https://images.unsplash.com/photo-1494972308805-463bc619d34e?w=400",
        "https://images.unsplash.com/photo-1505635552518-3b72ed6b11df?w=400",
        "https://images.unsplash.com/photo-1603126857599-f6e157fa2fe6?w=400",
    ],
    "Poesía": [
        "https://images.unsplash.com/photo-1474932430478-367dbb6832c1?w=400",
        "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=400",
        "https://images.unsplash.com/photo-1473186505569-9c61870c11f9?w=400",
        "https://images.unsplash.com/photo-1499257398675-4f1eb5357917?w=400",
    ],
    "Historia": [
        "https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=400",
        "https://images.unsplash.com/photo-1529867094037-62cb612ab829?w=400",
        "https://images.unsplash.com/photo-1604580864964-0462f5d5b1a8?w=400",
        "https://images.unsplash.com/photo-1447069387593-a5de0862481e?w=400",
    ],
    "Filosofía": [
        "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400",
        "https://images.unsplash.com/photo-1519682577862-22b62b24e493?w=400",
        "https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?w=400",
        "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400",
    ],
    "Autoayuda": [
        "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=400",
        "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400",
        "https://images.unsplash.com/photo-1488190211105-8b0e65b80b4e?w=400",
        "https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=400",
    ],
    "Romance": [
        "https://images.unsplash.com/photo-1474552226712-ac0f0961a954?w=400",
        "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=400",
        "https://images.unsplash.com/photo-1529590003495-b2646e2718bf?w=400",
        "https://images.unsplash.com/photo-1490633874781-1c63cc424610?w=400",
    ],
    "Aventura": [
        "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400",
        "https://images.unsplash.com/photo-1445538263539-a6c0aaef3bc9?w=400",
        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=400",
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=400",
    ],
    "Ciencia": [
        "https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=400",
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=400",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400",
        "https://images.unsplash.com/photo-1576319155264-99536e0be1ee?w=400",
    ],
    "Infantil": [
        "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=400",
        "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=400",
        "https://images.unsplash.com/photo-1471970394675-613138e45da3?w=400",
        "https://images.unsplash.com/photo-1529590003495-b2646e2718bf?w=400",
    ],
}


# ── Libros organizados por categoría ────────────────────────────────────────
BOOKS = [
    # ═══════════════════════════════════════════════════════════════════════
    # FICCIÓN (12 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Cien Años de Soledad", "Gabriel García Márquez",
     "Muchos años después, frente al pelotón de fusilamiento, el coronel Aureliano Buendía había de recordar aquella tarde remota en que su padre lo llevó a conocer el hielo. Macondo era entonces una aldea de veinte casas de barro y cañabrava construidas a la orilla de un río de aguas diáfanas que se precipitaban por un lecho de piedras pulidas, blancas y enormes como huevos prehistóricos. El mundo era tan reciente, que muchas cosas carecían de nombre, y para mencionarlas había que señalarlas con el dedo.",
     "Ficción", 0.0, 1892, 456, 4.8, 35),

    ("Rayuela", "Julio Cortázar",
     "¿Encontraría a la Maga? Tantas veces me había bastado asomarme, viniendo por la rue de Seine, al arco que da al Quai de Conti, y apenas la luz de ceniza y olivo que flota sobre el río me dejaba distinguir las formas, ya su silueta delgada se inscribía en el Pont des Arts. La Maga no sabía que yo la miraba y ahora no estaba mirando el río.",
     "Ficción", 0.0, 1456, 389, 4.6, 41),

    ("Pedro Páramo", "Juan Rulfo",
     "Vine a Comala porque me dijeron que acá vivía mi padre, un tal Pedro Páramo. Mi madre me lo dijo. Y yo le prometí que vendría a verlo en cuanto ella muriera. Y todavía antes me había dicho: No vayas a pedirle nada. Exígele lo nuestro. Lo que estuvo obligado a darme y nunca me dio. El olvido en que nos tuvo, mi hijo, cóbraselo caro.",
     "Ficción", 0.0, 1234, 298, 4.7, 32),

    ("La Casa de los Espíritus", "Isabel Allende",
     "Barrabás llegó a la familia por vía marítima, anotó la niña Clara con su delicada caligrafía. Ya entonces tenía el hábito de escribir las cosas importantes y más tarde, cuando se quedó muda, escribía también las trivialidades, sin sospechar que cincuenta años después sus cuadernos me servirían para rescatar la memoria del pasado.",
     "Ficción", 0.0, 987, 234, 4.5, 28),

    ("El Túnel", "Ernesto Sabato",
     "Bastará decir que soy Juan Pablo Castel, el pintor que mató a María Iribarne; supongo que el proceso está en el recuerdo de todos y que no se necesitan mayores explicaciones sobre mi persona. Aunque ni el diablo sabe qué es lo que ha de recordar la gente, ni por qué.",
     "Ficción", 0.0, 876, 213, 4.4, 25),

    ("Ficciones", "Jorge Luis Borges",
     "Debo la revelación de Uqbar a la conjunción de un espejo y de una enciclopedia. El espejo inquietaba el fondo de un corredor en una quinta de la calle Gaona, en Ramos Mejía; la enciclopedia falazmente se llama The Anglo-American Cyclopaedia y es una reimpresión literal de la Encyclopaedia Britannica de 1902.",
     "Ficción", 0.0, 1567, 423, 4.9, 47),

    ("Como Agua para Chocolate", "Laura Esquivel",
     "Tita tenía una manera muy particular de llorar desde que nació. Cuando estaba en el vientre de mamá Elena, lloraba tan fuerte que Nacha, la cocinera, la oía sin esforzarse. Dicen que cuando nació, en vez de llanto, soltó un chillido tan fuerte que provocó que el pastel que se estaba horneando se volteara.",
     "Ficción", 0.0, 1123, 267, 4.3, 22),

    ("El Amor en los Tiempos del Cólera", "Gabriel García Márquez",
     "Era inevitable: el olor de las almendras amargas le recordaba siempre el destino de los amores contrariados. El doctor Juvenal Urbino lo percibió desde que entró en la casa todavía en penumbras, adonde había acudido de urgencia a ocuparse de un caso que para él había dejado de ser urgente desde hacía muchos años.",
     "Ficción", 0.0, 1678, 445, 4.7, 38),

    ("La Sombra del Viento", "Carlos Ruiz Zafón",
     "Todavía recuerdo aquel amanecer en que mi padre me llevó por primera vez a visitar el Cementerio de los Libros Olvidados. Desgranaban los primeros días del verano de 1945 y caminábamos por las calles de una Barcelona atrapada bajo cielos de ceniza y un sol de vapor que se derramaba sobre la Rambla de Santa Mónica.",
     "Ficción", 0.0, 2134, 567, 4.6, 52),

    ("Aura", "Carlos Fuentes",
     "Lees ese anuncio: una oferta de esa naturaleza no se hace todos los días. Lees y relees el aviso. Parece dirigido a ti, a nadie más. Distraído, dejas que la ceniza del cigarro caiga dentro de la taza de té que has estado bebiendo en este cafetín sucio y barato.",
     "Ficción", 0.0, 654, 178, 4.5, 19),

    ("Los Detectives Salvajes", "Roberto Bolaño",
     "Fui cordialmente invitado a formar parte del realismo visceral. No hubo ceremonia de iniciación. Mejor así. La entrada al taller literario de Julio César Álamo se hizo por la puerta grande, o al menos eso pensé.",
     "Ficción", 0.0, 1345, 334, 4.4, 29),

    ("Crónica de una Muerte Anunciada", "Gabriel García Márquez",
     "El día en que lo iban a matar, Santiago Nasar se levantó a las 5.30 de la mañana para esperar el buque en que llegaba el obispo. Había soñado que atravesaba un bosque de higuerones donde caía una llovizna tierna, y por un instante fue feliz en el sueño.",
     "Ficción", 0.0, 1789, 412, 4.8, 44),

    # ═══════════════════════════════════════════════════════════════════════
    # CLÁSICOS (12 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Don Quijote de la Mancha", "Miguel de Cervantes",
     "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor. Una olla de algo más vaca que carnero, salpicón las más noches, duelos y quebrantos los sábados, lentejas los viernes.",
     "Clásicos", 0.0, 2345, 678, 4.9, 56),

    ("El Principito", "Antoine de Saint-Exupéry",
     "Aquí está mi secreto. Es muy simple: no se ve bien sino con el corazón. Lo esencial es invisible a los ojos. Los hombres de tu tierra cultivan cinco mil rosas en un mismo jardín y no encuentran lo que buscan. Y sin embargo, lo que buscan podría encontrarse en una sola rosa.",
     "Clásicos", 0.0, 3456, 890, 4.9, 67),

    ("Orgullo y Prejuicio", "Jane Austen",
     "Es una verdad universalmente reconocida que un hombre soltero, poseedor de una gran fortuna, necesita una esposa. Por poco que se conozcan los sentimientos o las opiniones de un hombre de esas características, esta verdad está tan arraigada en la mente de las familias vecinas que se le considera como legítima propiedad de alguna de sus hijas.",
     "Clásicos", 0.0, 1567, 423, 4.7, 39),

    ("Crimen y Castigo", "Fiódor Dostoievski",
     "A principios de julio, durante un calor sofocante, al atardecer, un joven salió de la minúscula habitación que tenía alquilada en la callejuela de S... y, lentamente, como si estuviera indeciso, se dirigió al puente de K... Había logrado esquivar el encuentro con su patrona en la escalera.",
     "Clásicos", 0.0, 1234, 345, 4.6, 33),

    ("Los Miserables", "Victor Hugo",
     "En 1815, monseñor Charles-François-Bienvenu Myriel era obispo de Digne. Era un anciano de unos setenta y cinco años que ocupaba la sede de Digne desde 1806. Aunque este detalle no afecta en nada al fondo de lo que vamos a referir, quizá no sea inútil, para ser exactos, indicar aquí los rumores y habladurías que habían corrido sobre su persona.",
     "Clásicos", 0.0, 1890, 501, 4.8, 42),

    ("La Odisea", "Homero",
     "Cuéntame, Musa, la historia del hombre de muchos senderos, que después de destruir la sacra ciudad de Troya anduvo peregrinando larguísimo tiempo, vio las poblaciones y conoció las costumbres de muchos hombres y padeció en su ánimo gran número de trabajos en su navegación por el ponto.",
     "Clásicos", 0.0, 1456, 389, 4.7, 35),

    ("Anna Karenina", "León Tolstói",
     "Todas las familias felices se parecen unas a otras; pero cada familia infeliz tiene un motivo especial para sentirse desgraciada. En casa de los Oblonski reinaba la confusión. La esposa había descubierto que su marido mantenía relaciones con la institutriz francesa.",
     "Clásicos", 0.0, 1678, 445, 4.6, 37),

    ("Hamlet", "William Shakespeare",
     "Ser o no ser: esa es la cuestión. ¿Cuál es más digna acción del ánimo, sufrir los tiros penetrantes de la fortuna injusta, u oponer los brazos a este torrente de calamidades, y darles fin con atrevida resistencia? Morir es dormir. ¿No más?",
     "Clásicos", 0.0, 1345, 367, 4.8, 40),

    ("La Divina Comedia", "Dante Alighieri",
     "A mitad del camino de la vida, en una selva oscura me encontraba porque mi ruta había extraviado. ¡Cuán dura cosa es decir cuál era esta salvaje selva, áspera y fuerte que en el pensamiento renueva el pavor!",
     "Clásicos", 0.0, 1123, 298, 4.7, 31),

    ("Madame Bovary", "Gustave Flaubert",
     "Nos hallábamos en la sala de estudio cuando entró el director seguido de un nuevo alumno vestido de paisano y de un bedel que traía un gran pupitre. Los que estaban dormidos se despertaron y todos se levantaron como sorprendidos en su trabajo.",
     "Clásicos", 0.0, 987, 234, 4.5, 26),

    ("El Conde de Montecristo", "Alejandro Dumas",
     "El 24 de febrero de 1815, el vigía de Notre-Dame de la Garde señaló al bergantín-goleta El Faraón procedente de Esmirna, Trieste y Nápoles. Un piloto costero se lanzó de inmediato del puerto y se dirigió al buque, que había redondeado el cabo Morgion.",
     "Clásicos", 0.0, 2123, 556, 4.6, 43),

    ("Las Mil y Una Noches", "Anónimo",
     "Cuentan que hace mucho tiempo vivía en una ciudad de Oriente un poderoso sultán que, herido por la traición de su esposa, juró vengarse de todas las mujeres. Cada noche tomaba una nueva esposa y al amanecer la mandaba ejecutar. Así fue hasta que llegó Sherezade.",
     "Clásicos", 0.0, 1567, 412, 4.5, 34),

    # ═══════════════════════════════════════════════════════════════════════
    # CIENCIA FICCIÓN (12 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("1984", "George Orwell",
     "Era un día luminoso y frío de abril y los relojes daban las trece. Winston Smith, con la barbilla clavada en el pecho en su esfuerzo por burlar el azote del viento, se deslizó rápidamente por las puertas de cristal de las Casas de la Victoria, aunque no con la rapidez suficiente como para evitar que un remolino de polvo entrara con él.",
     "Ciencia Ficción", 0.0, 2567, 678, 4.8, 55),

    ("Un Mundo Feliz", "Aldous Huxley",
     "Un edificio gris, achaparrado, de solo treinta y cuatro plantas. Encima de la entrada principal las palabras Centro de Incubación y Condicionamiento de la Central de Londres, y, en un escudo, la divisa del Estado Mundial: Comunidad, Identidad, Estabilidad.",
     "Ciencia Ficción", 0.0, 1890, 501, 4.7, 43),

    ("Fahrenheit 451", "Ray Bradbury",
     "Era un placer quemar. Era un placer especial ver las cosas consumidas, ver los objetos ennegrecidos y cambiados. Con la punta de bronce del soplete en sus puños, con aquella gigantesca serpiente escupiendo su petróleo venenoso sobre el mundo.",
     "Ciencia Ficción", 0.0, 1678, 445, 4.6, 38),

    ("Dune", "Frank Herbert",
     "En la semana que precedió a su partida hacia Arrakis, la vieja Reverenda Madre vino para poner a prueba a Paul. La anciana entró acompañada por la madre de Paul, la dama Jessica, que le indicó una silla en la que la anciana se dejó caer lentamente.",
     "Ciencia Ficción", 0.0, 1567, 423, 4.7, 40),

    ("Fundación", "Isaac Asimov",
     "Hari Seldon nació en el año 11.988 de la Era Galáctica. Su lugar de nacimiento fue Helicón, en el sector de Arturo, donde su padre fue cultivador de tabaco en los distritos hidropónicos del planeta. Según una tradición de dudosa autenticidad, su madre fue una retirada.",
     "Ciencia Ficción", 0.0, 1456, 389, 4.8, 45),

    ("Crónicas Marcianas", "Ray Bradbury",
     "Un minuto antes era invierno en Ohio, las puertas estaban cerradas, las ventanas cerradas, los cristales empañados por la escarcha, los carámbanos bordeaban todos los techos, los niños esquiaban en las laderas, y las amas de casa iban caminando pesadamente por las calles heladas como grandes osos negros.",
     "Ciencia Ficción", 0.0, 1234, 312, 4.5, 30),

    ("Neuromante", "William Gibson",
     "El cielo sobre el puerto tenía el color de una pantalla de televisor sintonizado en un canal muerto. Case oía las bocinas de los puestos de fideos en el Sprawl, olía el plástico quemado, veía cómo la neón de la cervecería de al lado le bañaba las manos pálidas.",
     "Ciencia Ficción", 0.0, 876, 213, 4.4, 22),

    ("El Juego de Ender", "Orson Scott Card",
     "Creo que es imposible que sepamos lo que ocurre. Pienso que lo mejor sería no tener monitor. Pero yo sabía desde el principio que serían difíciles de criar. Quizá lo mejor sea esperar un poco.",
     "Ciencia Ficción", 0.0, 1345, 345, 4.6, 35),

    ("2001: Una Odisea del Espacio", "Arthur C. Clarke",
     "La sequía había durado ya diez millones de años, y el reinado de los terribles saurios tiempo ha que había terminado. Aquí, en el Ecuador del continente que un día sería conocido como África, la batalla por la existencia había alcanzado un nuevo clímax de ferocidad.",
     "Ciencia Ficción", 0.0, 1123, 278, 4.5, 27),

    ("Solaris", "Stanislaw Lem",
     "A las diecinueve horas del tiempo de a bordo descendí por la escala metálica de la cápsula interior y me introduje en la cabina. Apenas cabíamos los dos, Moddard y yo. Nos sentamos uno frente a otro, con las rodillas casi tocándose.",
     "Ciencia Ficción", 0.0, 765, 189, 4.3, 18),

    ("La Guerra de los Mundos", "H. G. Wells",
     "Nadie hubiera creído, en los últimos años del siglo diecinueve, que los asuntos humanos eran observados aguda y atentamente por inteligencias más desarrolladas que la del hombre y sin embargo tan mortales como él; que mientras los hombres se ocupaban de sus cosas eran examinados y estudiados.",
     "Ciencia Ficción", 0.0, 1567, 401, 4.6, 36),

    ("El Marciano", "Andy Weir",
     "Estoy jodido. Esa es mi opinión considerada. Jodido. Seis días en lo que debería ser la mayor aventura de mi vida y se ha convertido en una pesadilla. Ni siquiera sé quién leerá esto. Supongo que alguien lo encontrará algún día.",
     "Ciencia Ficción", 0.0, 2345, 612, 4.7, 48),

    # ═══════════════════════════════════════════════════════════════════════
    # TERROR (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("It", "Stephen King",
     "El acontecimiento que llegó a conocerse como la tragedia del Canal de Derry tuvo lugar el 15 de octubre de 1957. Aquel día llovía a cántaros. George Denbrough estaba en el sótano de su casa mirando cómo su hermano mayor, Bill, aplicaba parafina caliente en las junturas de un barco de papel de periódico.",
     "Terror", 0.0, 2345, 612, 4.6, 48),

    ("Drácula", "Bram Stoker",
     "3 de mayo. Bistritz. Salí de Múnich a las ocho de la noche del primero de mayo, y llegué a Viena a primera hora de la mañana siguiente. Debería haber llegado a las seis cuarenta y seis, pero el tren llevaba una hora de retraso. Budapest me pareció un lugar maravilloso.",
     "Terror", 0.0, 1678, 445, 4.5, 37),

    ("Frankenstein", "Mary Shelley",
     "No esperará usted que, en el transcurso de mi viaje de descubrimiento y placer, mis desventuras se refieran a un mal tan grande. He llegado ayer a este lugar, y mi primera preocupación ha sido asegurar a mi querida hermana de mi bienestar y de mi creciente confianza en el éxito de la empresa.",
     "Terror", 0.0, 1345, 345, 4.4, 29),

    ("El Resplandor", "Stephen King",
     "Jack Torrance pensó: ve a cualquier otro sitio del mundo, pero no vayas allí. Sin embargo, no se desvió de su camino. La entrevista era a la una en punto, hora de montaña, en la oficina del señor Ullman.",
     "Terror", 0.0, 1890, 501, 4.7, 42),

    ("La Llamada de Cthulhu", "H. P. Lovecraft",
     "No hay en el mundo fortuna mayor, creo, que la incapacidad de la mente humana para relacionar entre sí todo lo que hay en ella. Vivimos en una plácida isla de ignorancia en medio de negros mares de infinitud, y no es nuestro destino viajar lejos.",
     "Terror", 0.0, 1123, 298, 4.6, 31),

    ("El Exorcista", "William Peter Blatty",
     "Al inicio, en la explanada de Nínive, el viejo sacerdote notó cómo los dedos le temblaban entre los fragmentos del pasado. Se estremeció con una punzada de presagio. Algo se acercaba. Lo sentía como un animal siente un terremoto antes de que la tierra empiece a temblar.",
     "Terror", 0.0, 987, 234, 4.3, 22),

    ("Cementerio de Animales", "Stephen King",
     "Louis Creed, que había perdido a su padre a los tres años y que no tenía ningún recuerdo de él, encontró padre a los treinta y ocho, una edad avanzada para semejante descubrimiento. El nombre de su padre era Irwin Goldman.",
     "Terror", 0.0, 1234, 312, 4.5, 27),

    ("El Fantasma de la Ópera", "Gastón Leroux",
     "Existió realmente el fantasma de la Ópera. No fue, como durante mucho tiempo se creyó, una inspiración de los artistas, una superstición de los directores, una creación falaz de los cerebros excitados de aquellas señoritas del cuerpo de baile.",
     "Terror", 0.0, 876, 213, 4.2, 19),

    ("La Maldición de Hill House", "Shirley Jackson",
     "Ningún organismo vivo puede existir de manera saludable bajo condiciones de realidad absoluta; hasta las alondras y las langostas sueñan, según dicen. Hill House, que no estaba sana, se alzaba sola contra sus colinas, acunando su oscuridad.",
     "Terror", 0.0, 765, 189, 4.4, 20),

    ("Misery", "Stephen King",
     "Aaug. Número uno con la estrella de plata. ¡Voy a ser el número uno con la estrella de plata! La voz que lo dijo estaba llena de una horrorosa alegría. Flotaba entre la oscuridad y el dolor.",
     "Terror", 0.0, 1456, 378, 4.5, 33),

    # ═══════════════════════════════════════════════════════════════════════
    # POESÍA (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Veinte Poemas de Amor y una Canción Desesperada", "Pablo Neruda",
     "Puedo escribir los versos más tristes esta noche. Escribir, por ejemplo: «La noche está estrellada, y tiritan, azules, los astros, a lo lejos.» El viento de la noche gira en el cielo y canta. Puedo escribir los versos más tristes esta noche. Yo la quise, y a veces ella también me quiso.",
     "Poesía", 0.0, 2345, 612, 4.9, 55),

    ("Canto General", "Pablo Neruda",
     "Antes de la peluca y la casaca fueron los ríos, ríos arteriales: fueron las cordilleras, en cuya onda raída el cóndor o la nieve parecían inmóviles: fue la humedad y la espesura, el trueno sin nombre todavía, las pampas planetarias.",
     "Poesía", 0.0, 1234, 312, 4.7, 35),

    ("Poeta en Nueva York", "Federico García Lorca",
     "Asesinado por el cielo, entre las formas que van hacia la sierpe y las formas que buscan el cristal, dejaré crecer mis cabellos. Con el árbol de muñones que no canta y el niño con el blanco rostro de huevo.",
     "Poesía", 0.0, 1123, 298, 4.6, 30),

    ("Romancero Gitano", "Federico García Lorca",
     "La luna vino a la fragua con su polisón de nardos. El niño la mira, mira. El niño la está mirando. En el aire conmovido mueve la luna sus brazos y enseña, lúbrica y pura, sus senos de duro estaño.",
     "Poesía", 0.0, 1567, 423, 4.8, 42),

    ("Altazor", "Vicente Huidobro",
     "Nací a los treinta y tres años, el día de la muerte de Cristo; nací en el Equinoccio, bajo las hortensias y los aeroplanos del calor. Tenía yo un profundo mirar de pichón, de túnel y de automóvil sentimental.",
     "Poesía", 0.0, 654, 178, 4.5, 18),

    ("Trilce", "César Vallejo",
     "Hay un lugar que yo me sé en este mundo, nada menos, adonde nunca llegamos. Donde, aun de noche, el hombrecito acuesta las iniciales de su nombre, la caricia de su último amor herido.",
     "Poesía", 0.0, 567, 145, 4.4, 15),

    ("Los Heraldos Negros", "César Vallejo",
     "Hay golpes en la vida, tan fuertes... ¡Yo no sé! Golpes como del odio de Dios; como si ante ellos, la resaca de todo lo sufrido se empozara en el alma... ¡Yo no sé! Son pocos; pero son... Abren zanjas oscuras en el rostro más fiero y en el lomo más fuerte.",
     "Poesía", 0.0, 876, 234, 4.7, 28),

    ("Piedra de Sol", "Octavio Paz",
     "Un sauce de cristal, un chopo de agua, un alto surtidor que el viento arquea, un árbol bien plantado mas danzante, un caminar de río que se curva, avanza, retrocede, da un rodeo y llega siempre.",
     "Poesía", 0.0, 765, 189, 4.6, 22),

    ("Hojas de Hierba", "Walt Whitman",
     "Me celebro y me canto a mí mismo. Y lo que yo diga ahora de mí, lo digo de ti, porque lo que yo tengo lo tienes tú y cada átomo de mi cuerpo es tuyo también.",
     "Poesía", 0.0, 1345, 356, 4.8, 38),

    ("Cien Sonetos de Amor", "Pablo Neruda",
     "Matilde, nombre de planta o piedra o vino, de lo que nace de la tierra y dura, palabra en cuyo crecimiento amanece, en cuyo estío estalla la luz de los limones.",
     "Poesía", 0.0, 1678, 445, 4.9, 47),

    # ═══════════════════════════════════════════════════════════════════════
    # HISTORIA (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Sapiens: De Animales a Dioses", "Yuval Noah Harari",
     "Hace cien mil años, al menos seis especies de humanos habitaban la Tierra. Hoy solo queda una, la nuestra: Homo sapiens. ¿Cómo logró nuestra especie imponerse en la lucha por la existencia? ¿Por qué nuestros ancestros recolectores se unieron para crear ciudades y reinos?",
     "Historia", 0.0, 2567, 678, 4.8, 55),

    ("El Arte de la Guerra", "Sun Tzu",
     "La guerra es de vital importancia para el Estado; es el dominio de la vida o de la muerte, el camino hacia la supervivencia o la pérdida del Imperio: es forzoso manejarla bien. No reflexionar seriamente sobre todo lo que le concierne es dar prueba de una culpable indiferencia.",
     "Historia", 0.0, 1890, 501, 4.7, 43),

    ("Breve Historia del Mundo", "Ernst H. Gombrich",
     "Érase una vez... así empiezan todos los cuentos de hadas. Y cuando oímos estas palabras, sabemos que no se trata de nada real, de nada que haya sucedido realmente. Pero la historia del mundo comienza de verdad con un érase una vez, y todo lo que cuento a continuación ha sucedido realmente.",
     "Historia", 0.0, 1234, 312, 4.5, 30),

    ("Los Conquistadores", "Matthew Restall",
     "La conquista de América fue uno de los eventos más transformadores de la historia humana. En pocas décadas, imperios que habían florecido durante siglos cayeron ante un puñado de aventureros europeos. Pero la realidad fue mucho más compleja de lo que nos han contado.",
     "Historia", 0.0, 876, 213, 4.3, 22),

    ("El Diario de Ana Frank", "Ana Frank",
     "Espero poder confiártelo todo como aún no lo he podido hacer con nadie, y espero que seas para mí un gran apoyo. 12 de junio de 1942. Espero que tú lo seas todo para mí.",
     "Historia", 0.0, 2123, 567, 4.8, 50),

    ("Memorias de Adriano", "Marguerite Yourcenar",
     "Querido Marco: Hoy he ido a ver a mi médico Hermógenes, que acaba de regresar a la Villa tras un largo viaje por Asia. No he querido fiarme de ningún otro, y he esperado su regreso para que me examine. Nada de lo que pueda decirme me asustará.",
     "Historia", 0.0, 987, 234, 4.6, 26),

    ("Historia de Dos Ciudades", "Charles Dickens",
     "Era el mejor de los tiempos, era el peor de los tiempos, la edad de la sabiduría, y también de la locura; la época de las creencias y de la incredulidad; la era de la luz y de las tinieblas; la primavera de la esperanza y el invierno de la desesperación.",
     "Historia", 0.0, 1456, 389, 4.5, 34),

    ("21 Lecciones para el Siglo XXI", "Yuval Noah Harari",
     "En un mundo inundado de información irrelevante, la claridad es poder. La censura no funciona bloqueando el flujo de información, sino más bien inundando a la gente de desinformación y distracciones.",
     "Historia", 0.0, 1678, 445, 4.6, 38),

    ("Las Venas Abiertas de América Latina", "Eduardo Galeano",
     "La división internacional del trabajo consiste en que unos países se especializan en ganar y otros en perder. Nuestra comarca del mundo, que hoy llamamos América Latina, fue precoz: se especializó en perder desde los remotos tiempos.",
     "Historia", 0.0, 1567, 412, 4.7, 41),

    ("El Laberinto de la Soledad", "Octavio Paz",
     "A todos, en algún momento, se nos ha revelado nuestra existencia como algo particular, intransferible y precioso. Casi siempre esta revelación se sitúa en la adolescencia. El descubrimiento de nosotros mismos se manifiesta como un sabernos solos.",
     "Historia", 0.0, 1123, 298, 4.6, 29),

    # ═══════════════════════════════════════════════════════════════════════
    # FILOSOFÍA (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("El Mundo de Sofía", "Jostein Gaarder",
     "Sofía Amundsen volvía a casa después del colegio. La primera parte del camino la había hecho en compañía de Jorunn. Habían hablado de robots. Jorunn opinaba que el cerebro humano era como un ordenador muy avanzado. Sofía no estaba segura de estar de acuerdo.",
     "Filosofía", 0.0, 1890, 501, 4.6, 43),

    ("Así Habló Zaratustra", "Friedrich Nietzsche",
     "Cuando Zaratustra tenía treinta años abandonó su patria y el lago de su patria y marchó a las montañas. Allí gozó de su espíritu y de su soledad y durante diez años no se cansó de hacerlo.",
     "Filosofía", 0.0, 1345, 356, 4.5, 33),

    ("La República", "Platón",
     "Bajé ayer al Pireo con Glaucón, hijo de Aristón, para rogar a la diosa, y deseando ver al mismo tiempo cómo realizaban la fiesta que iba a celebrarse por primera vez. Me pareció hermosa la procesión de los habitantes de la ciudad.",
     "Filosofía", 0.0, 1123, 298, 4.7, 30),

    ("Meditaciones", "Marco Aurelio",
     "De mi abuelo Vero aprendí el buen carácter y la serenidad. De la reputación y memoria legada por mi progenitor, la discreción y la hombría. De mi madre, el respeto a los dioses, la generosidad y la abstención de obrar mal.",
     "Filosofía", 0.0, 1234, 312, 4.8, 36),

    ("El Banquete", "Platón",
     "Pues bien, Erixímaco, ya que tú has pronunciado un bello discurso en honor de Eros, es justo que yo intente hacerlo también. Pero voy a intentar elogiarlo de un modo distinto al tuyo y al de Pausanias.",
     "Filosofía", 0.0, 876, 213, 4.4, 22),

    ("El Ser y la Nada", "Jean-Paul Sartre",
     "La existencia precede a la esencia. Lo que significa que el hombre empieza por existir, se encuentra, surge en el mundo, y después se define. El hombre, tal como lo concibe el existencialista, si no es definible, es porque empieza por no ser nada.",
     "Filosofía", 0.0, 654, 178, 4.3, 17),

    ("El Arte de Amar", "Erich Fromm",
     "¿Es el amor un arte? En tal caso, requiere conocimiento y esfuerzo. ¿O es el amor una sensación placentera, cuya experiencia es una cuestión de azar, algo con lo que uno tropieza si tiene suerte?",
     "Filosofía", 0.0, 1567, 423, 4.7, 39),

    ("Ética para Amador", "Fernando Savater",
     "A veces, hijo mío, me gustaría que estuvieras todavía en la edad de los cuentos de hadas. No porque me parezca mal que hayas crecido — ya sabes que las criaturas que no crecen dan bastante pena, como Peter Pan — sino porque me resultaría más fácil contarte ciertas cosas.",
     "Filosofía", 0.0, 1456, 389, 4.5, 34),

    ("Elogio de la Locura", "Erasmo de Rotterdam",
     "Por más que los mortales hablen de mí como gusten — pues no ignoro cuánto descrédito tiene la Locura aun entre los más locos — soy yo, sin embargo, y yo sola, la que con mi divino influjo alegro a los dioses y a los hombres.",
     "Filosofía", 0.0, 765, 189, 4.4, 20),

    ("El Príncipe", "Nicolás Maquiavelo",
     "Todos los estados, todos los dominios que han tenido y tienen imperio sobre los hombres, han sido y son o repúblicas o principados. Los principados son o hereditarios, cuando el linaje de su señor los ha poseído durante largo tiempo, o son nuevos.",
     "Filosofía", 0.0, 1678, 445, 4.6, 37),

    # ═══════════════════════════════════════════════════════════════════════
    # AUTOAYUDA (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("El Alquimista", "Paulo Coelho",
     "El muchacho se llamaba Santiago. Llegaba al final del día a una iglesia abandonada. El techo se había derrumbado hacía mucho tiempo y un enorme sicomoro había crecido en el lugar que antes ocupaba la sacristía. Decidió pasar allí la noche.",
     "Autoayuda", 0.0, 3456, 890, 4.5, 65),

    ("Los 7 Hábitos de la Gente Altamente Efectiva", "Stephen Covey",
     "Entre el estímulo y la respuesta, el ser humano tiene la libertad interior de elegir. En esa libertad radican las cualidades que nos hacen singularmente humanos: la autoconciencia, la imaginación, la conciencia moral y la voluntad independiente.",
     "Autoayuda", 0.0, 1890, 501, 4.6, 43),

    ("El Poder del Ahora", "Eckhart Tolle",
     "¿Puedes sentir tu existencia en este momento? No me refiero a tu historia personal, a tu pasado, a los problemas que tienes. Me refiero a algo más profundo. ¿Puedes sentir la presencia que eres, la conciencia pura que está leyendo estas palabras?",
     "Autoayuda", 0.0, 1567, 423, 4.7, 39),

    ("Padre Rico, Padre Pobre", "Robert Kiyosaki",
     "Tuve dos padres, uno rico y uno pobre. Uno era muy instruido e inteligente; tenía un doctorado y había completado cuatro años de trabajo de grado en menos de dos años. El otro padre ni siquiera completó el octavo grado.",
     "Autoayuda", 0.0, 2345, 612, 4.4, 50),

    ("Hábitos Atómicos", "James Clear",
     "Aquí va una pregunta que la mayoría de la gente no se plantea: si mejoraras un uno por ciento cada día durante un año, ¿cuánto habrías mejorado al final? La mayoría de la gente piensa que habría mejorado un 365 por ciento. En realidad, serías 37 veces mejor.",
     "Autoayuda", 0.0, 2567, 678, 4.8, 55),

    ("El Monje que Vendió su Ferrari", "Robin Sharma",
     "No puedo creer que sea él, pensé mientras miraba la figura deteriorada que se encontraba ante mí. Las grandes ojeras que rodeaban sus ojos, las arrugas profundas que surcaban su cara y la apariencia cadavérica apenas me permitían reconocer al hombre que una vez había sido.",
     "Autoayuda", 0.0, 1234, 312, 4.3, 28),

    ("Piense y Hágase Rico", "Napoleon Hill",
     "En verdad, los pensamientos son cosas, y cosas poderosas, cuando se mezclan con un propósito definido, persistencia y un ardiente deseo de traducirlos en riquezas u otros objetos materiales.",
     "Autoayuda", 0.0, 1678, 445, 4.5, 37),

    ("El Sutil Arte de que No te Importe Nada", "Mark Manson",
     "Charles Bukowski era un alcohólico, un mujeriego, un jugador crónico, un tacaño, un vago, y en sus peores días, un poeta. Probablemente es el último hombre en la Tierra del que esperarías encontrar en un libro de autoayuda.",
     "Autoayuda", 0.0, 1890, 501, 4.6, 42),

    ("Los Cuatro Acuerdos", "Miguel Ruiz",
     "Todo lo que hacemos está basado en acuerdos que hemos hecho: acuerdos con nosotros mismos, con otras personas, con Dios, con la vida. Pero los acuerdos más importantes son los que hacemos con nosotros mismos.",
     "Autoayuda", 0.0, 1456, 389, 4.7, 35),

    ("Inteligencia Emocional", "Daniel Goleman",
     "En un sentido muy real, tenemos dos mentes, una que piensa y otra que siente. Estas dos formas fundamentalmente diferentes de conocimiento interactúan para construir nuestra vida mental. La mente racional es la forma de comprensión de la que somos típicamente conscientes.",
     "Autoayuda", 0.0, 1345, 356, 4.5, 33),

    # ═══════════════════════════════════════════════════════════════════════
    # ROMANCE (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Romeo y Julieta", "William Shakespeare",
     "Dos familias iguales en nobleza, en la hermosa Verona donde situamos nuestra escena, renuevan un viejo rencor que estalla en nuevos disturbios, donde la sangre ciudadana mancha ciudadanas manos. De las entrañas fatales de estos dos enemigos nace una pareja de amantes de mala estrella.",
     "Romance", 0.0, 2345, 612, 4.8, 50),

    ("Cumbres Borrascosas", "Emily Brontë",
     "Acabo de regresar de una visita a mi casero, el solitario vecino que va a darme algún que otro problema. Este es, sin duda, un hermoso país. En toda Inglaterra no creo que hubiera podido encontrar un sitio tan completamente apartado del mundanal ruido.",
     "Romance", 0.0, 1567, 423, 4.6, 38),

    ("Jane Eyre", "Charlotte Brontë",
     "No había posibilidad de pasear ese día. Por la mañana habíamos estado vagando durante una hora por entre los setos pelados del jardín. Después de comer, el frío viento invernal trajo consigo unas nubes tan sombrías y una lluvia tan penetrante.",
     "Romance", 0.0, 1345, 356, 4.7, 35),

    ("El Fantasma de Canterville", "Oscar Wilde",
     "Cuando el señor Hiram B. Otis, ministro de Estados Unidos, compró Canterville Chase, todo el mundo le dijo que estaba haciendo algo muy tonto, pues no cabía ninguna duda de que la casa estaba embrujada.",
     "Romance", 0.0, 876, 213, 4.4, 22),

    ("Persuasión", "Jane Austen",
     "Sir Walter Elliot, de la residencia Kellynch, en Somersetshire, era un hombre que por diversión nunca tomaba otro libro que el de Nobleza. Allí encontraba ocupación para una hora ociosa, y consuelo en una hora de angustia.",
     "Romance", 0.0, 987, 234, 4.5, 26),

    ("Las Batallas en el Desierto", "José Emilio Pacheco",
     "Me acuerdo, no me acuerdo: ¿qué año era aquél? Ya existía la televisión pero todavía no llegaba a México o apenas la estaban probando. Yo no la veía porque ni siquiera tenía radio. Las canciones que fueron la música de fondo de aquel año las escuchaba en casa de mi vecina.",
     "Romance", 0.0, 1234, 312, 4.6, 30),

    ("Doctor Zhivago", "Boris Pasternak",
     "Iban y cantaban «Eterna memoria», y entre canción y canción era como si el golpe de los pies, los caballos y las ráfagas de viento continuaran cantando lo que ya no se cantaba. Los transeúntes cedían el paso al cortejo.",
     "Romance", 0.0, 1123, 278, 4.5, 27),

    ("La Dama de las Camelias", "Alejandro Dumas (hijo)",
     "En mi opinión, solo se pueden crear personajes después de haber estudiado mucho a los hombres, como solo se puede hablar una lengua después de haberla aprendido seriamente. Aún no tengo la edad suficiente como para inventar; me limito a contar.",
     "Romance", 0.0, 765, 189, 4.3, 18),

    ("El Amor en los Tiempos de la Peste", "Carlos Ruiz Zafón",
     "Barcelona, 1920. Un joven aprendiz en una librería de la calle Santa Ana descubre un libro misterioso que cambiará el curso de su vida. Entre las páginas amarillentas de aquel volumen, encontrará una historia de amor que desafía al tiempo y a la muerte.",
     "Romance", 0.0, 1456, 378, 4.4, 32),

    ("Corazón", "Edmundo de Amicis",
     "Hoy, primer día de escuela. ¡Pasaron como un sueño aquellos tres meses de vacaciones en el campo! Mi madre me llevó esta mañana a la sección Baretti a inscribirme para el tercer año elemental.",
     "Romance", 0.0, 654, 167, 4.2, 16),

    # ═══════════════════════════════════════════════════════════════════════
    # AVENTURA (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("La Isla del Tesoro", "Robert Louis Stevenson",
     "El caballero Trelawney, el doctor Livesey y los demás caballeros me han encargado que escriba todo lo relativo a la Isla del Tesoro, de cabo a rabo, sin dejarme más que la situación de la isla, y esto porque todavía hay en ella tesoros no descubiertos.",
     "Aventura", 0.0, 1890, 501, 4.6, 43),

    ("Veinte Mil Leguas de Viaje Submarino", "Julio Verne",
     "El año 1866 quedó marcado por un acontecimiento extraño, un fenómeno inexplicable e inexplicado que nadie ha podido olvidar. Sin mencionar los rumores que agitaron a las poblaciones de los puertos y sobreexcitaron la opinión pública en el interior de los continentes.",
     "Aventura", 0.0, 1678, 445, 4.5, 38),

    ("El Señor de los Anillos", "J. R. R. Tolkien",
     "Cuando el señor Bilbo Bolsón de Bolsón Cerrado anunció que muy pronto celebraría su cumpleaños centésimo decimoprimero con una fiesta de especial magnificencia, hubo muchos comentarios y excitación en Hobbiton.",
     "Aventura", 0.0, 3456, 890, 4.9, 67),

    ("El Hobbit", "J. R. R. Tolkien",
     "En un agujero en el suelo, vivía un hobbit. No un agujero húmedo, sucio, repugnante, con restos de gusanos y olor a fango, ni tampoco un agujero seco, desnudo y arenoso, sin nada en que sentarse o que comer: era un agujero-hobbit, y eso significa comodidad.",
     "Aventura", 0.0, 2567, 678, 4.8, 55),

    ("Las Aventuras de Tom Sawyer", "Mark Twain",
     "—¡Tom! ¡Tom! No hubo respuesta. —¡Tom! No hubo respuesta. —¿Dónde andará metido ese chico? ¡TOM! La anciana señora se bajó las gafas y miró por encima de ellas alrededor del cuarto.",
     "Aventura", 0.0, 1234, 312, 4.5, 30),

    ("Robinson Crusoe", "Daniel Defoe",
     "Nací en el año 1632, en la ciudad de York, de una buena familia, aunque no del país, pues mi padre era un extranjero de Bremen, que primeramente se había establecido en Hull. Consiguió una buena fortuna por medio del comercio.",
     "Aventura", 0.0, 1345, 356, 4.4, 33),

    ("La Vuelta al Mundo en 80 Días", "Julio Verne",
     "En el año 1872 la casa número 7 de Saville Row, Burlington Gardens — la casa en la que murió Sheridan en 1816 — estaba habitada por Phileas Fogg, esq., uno de los miembros más singulares y notados del Reform Club de Londres.",
     "Aventura", 0.0, 1567, 412, 4.6, 36),

    ("Moby Dick", "Herman Melville",
     "Llamadme Ismael. Hace unos años — no importa cuánto exactamente — teniendo poco o ningún dinero en el bolsillo, y nada en particular que me interesara en tierra, pensé que podría hacerme a la mar y ver la parte acuática del mundo.",
     "Aventura", 0.0, 1123, 298, 4.5, 28),

    ("Los Tres Mosqueteros", "Alejandro Dumas",
     "El primer lunes del mes de abril de 1625, el municipio de Meung, en el que nació el autor del Roman de la Rose, parecía hallarse en una revolución tan completa como si los hugonotes acabaran de hacer de ella una segunda La Rochelle.",
     "Aventura", 0.0, 1890, 501, 4.7, 42),

    ("Viaje al Centro de la Tierra", "Julio Verne",
     "El 24 de mayo de 1863, un domingo, mi tío, el profesor Lidenbrock, regresó precipitadamente a su casita situada en el número 19 de Königstrasse, una de las calles más antiguas del barrio viejo de Hamburgo.",
     "Aventura", 0.0, 987, 234, 4.4, 24),

    # ═══════════════════════════════════════════════════════════════════════
    # CIENCIA (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Cosmos", "Carl Sagan",
     "El Cosmos es todo lo que es, o lo que fue, o lo que será alguna vez. Nuestras contemplaciones más tibias del Cosmos nos conmueven: un escalofrío recorre nuestro espinazo, hay una voz que no se oye, una ligera sensación como de un recuerdo lejano.",
     "Ciencia", 0.0, 2345, 612, 4.8, 50),

    ("Breve Historia del Tiempo", "Stephen Hawking",
     "¿De dónde viene el universo? ¿Cómo y por qué empezó? ¿Tendrá un final, y en caso afirmativo, cómo será? Estas son preguntas que interesan a todos nosotros. Pero la ciencia moderna ha llegado a ser tan técnica que solo un número muy pequeño de especialistas son capaces de dominar las matemáticas.",
     "Ciencia", 0.0, 2567, 678, 4.9, 55),

    ("El Gen Egoísta", "Richard Dawkins",
     "La vida inteligente sobre un planeta alcanza su mayoría de edad cuando resuelve por primera vez el problema de su propia existencia. Si alguna vez visitan la Tierra criaturas superiores procedentes del espacio, la primera pregunta que formularán será: ¿Han descubierto ya la evolución?",
     "Ciencia", 0.0, 1234, 312, 4.6, 30),

    ("El Universo en una Cáscara de Nuez", "Stephen Hawking",
     "Albert Einstein, la Teoría de la Relatividad y los años que la precedieron. Einstein dejó un legado intelectual sin igual en la historia de la física. ¿En qué consistía exactamente su contribución y cómo surgió?",
     "Ciencia", 0.0, 1567, 423, 4.7, 38),

    ("Astrofísica para Gente con Prisa", "Neil deGrasse Tyson",
     "En el comienzo, casi catorce mil millones de años atrás, toda la materia y toda la energía de todo el universo conocido estaban concentradas en un volumen más pequeño que una billonésima del tamaño del punto que hay al final de esta oración.",
     "Ciencia", 0.0, 1890, 501, 4.7, 43),

    ("El Origen de las Especies", "Charles Darwin",
     "Cuando se comparan los individuos de la misma variedad o subvariedad de nuestras plantas y animales cultivados más antiguos, una de las primeras cosas que nos impresiona es que difieren generalmente más entre sí que los individuos de cualquier especie en estado natural.",
     "Ciencia", 0.0, 1123, 298, 4.5, 27),

    ("La Estructura de las Revoluciones Científicas", "Thomas Kuhn",
     "La historia, si se la considerara como algo más que un depósito de anécdotas o cronología, podría producir una transformación decisiva de la imagen que tenemos actualmente de la ciencia. Esa imagen ha sido trazada, incluso por los propios científicos, principalmente a partir del estudio de los logros científicos acabados.",
     "Ciencia", 0.0, 876, 213, 4.4, 22),

    ("La Doble Hélice", "James Watson",
     "Nunca he visto a Francis Crick con un talante modesto. Quizá en otros aspectos sí lo sea, pero no he tenido la fortuna de presenciarlo. Lo cual no quiere decir que sea presumido. Solo es que conoce su valor.",
     "Ciencia", 0.0, 765, 189, 4.3, 18),

    ("Seis Piezas Fáciles", "Richard Feynman",
     "Si en algún cataclismo se destruyeran todos los conocimientos científicos y solo se pudiera transmitir una frase a la siguiente generación de criaturas, ¿qué enunciado contendría la mayor información en menos palabras?",
     "Ciencia", 0.0, 1345, 356, 4.7, 34),

    ("Un Punto Azul Pálido", "Carl Sagan",
     "Mira ese punto. Eso es aquí. Eso es casa. Eso somos nosotros. En él, todos los que amas, todos los que conoces, todos de los que alguna vez oíste hablar, cada ser humano que existió, vivió allí su vida.",
     "Ciencia", 0.0, 1678, 445, 4.8, 42),

    # ═══════════════════════════════════════════════════════════════════════
    # INFANTIL (10 libros)
    # ═══════════════════════════════════════════════════════════════════════
    ("Charlie y la Fábrica de Chocolate", "Roald Dahl",
     "Estos dos viejecitos son el padre y la madre del señor Bucket. Se llaman Abuelo Joe y Abuela Josephine. Y estos dos viejecitos son el padre y la madre de la señora Bucket. Se llaman Abuelo George y Abuela Georgina.",
     "Infantil", 0.0, 2345, 612, 4.7, 50),

    ("Matilda", "Roald Dahl",
     "Es una cosa curiosa que los padres tiendan a creer que sus hijos son los más hermosos del mundo. Esto se puede comprender. Lo que no se puede comprender es por qué los padres de Matilda le prestaban tan poca atención.",
     "Infantil", 0.0, 1890, 501, 4.8, 45),

    ("Las Crónicas de Narnia: El León, la Bruja y el Ropero", "C. S. Lewis",
     "Érase una vez cuatro niños cuyos nombres eran Peter, Susan, Edmund y Lucy. Esta historia cuenta algo que les sucedió cuando los enviaron fuera de Londres durante la guerra, a causa de los bombardeos aéreos.",
     "Infantil", 0.0, 2123, 567, 4.7, 48),

    ("Harry Potter y la Piedra Filosofal", "J. K. Rowling",
     "El señor y la señora Dursley, del número 4 de Privet Drive, estaban orgullosos de decir que eran perfectamente normales, muchas gracias. Eran las últimas personas que esperarías que estuvieran involucradas en algo extraño o misterioso.",
     "Infantil", 0.0, 3456, 890, 4.9, 67),

    ("El Diario de Greg", "Jeff Kinney",
     "Primero que nada, quiero aclarar una cosa: esto es un DIARIO, no un querido diario. Ya sé lo que dice la portada. Cuando mamá lo compró le dije específicamente que no lo quisiera con las palabras querido diario en la portada.",
     "Infantil", 0.0, 1567, 423, 4.5, 38),

    ("James y el Melocotón Gigante", "Roald Dahl",
     "Hasta los cuatro años, James Henry Trotter había tenido una vida feliz. Vivía en paz con su madre y su padre en una bonita casa junto al mar. Siempre había otros niños con los que jugar.",
     "Infantil", 0.0, 1123, 298, 4.4, 27),

    ("Donde Viven los Monstruos", "Maurice Sendak",
     "La noche que Max se puso su traje de lobo e hizo bribonadas de una clase y de otra, su mamá lo llamó monstruo salvaje y Max dijo: Te voy a comer. Y lo mandaron a la cama sin cenar.",
     "Infantil", 0.0, 987, 234, 4.6, 30),

    ("El Principito", "Antoine de Saint-Exupéry",
     "Cuando yo tenía seis años vi en un libro sobre la selva virgen que se titulaba Historias Vividas, una magnífica lámina. En ella se representaba una serpiente boa que se tragaba a una fiera.",
     "Infantil", 0.0, 2567, 678, 4.9, 55),

    ("Alicia en el País de las Maravillas", "Lewis Carroll",
     "Alicia empezaba a cansarse de estar sentada con su hermana a la orilla del río, sin tener nada que hacer. De vez en cuando echaba una ojeada al libro que su hermana estaba leyendo, pero no tenía dibujos ni diálogos.",
     "Infantil", 0.0, 1678, 445, 4.6, 38),

    ("Cuentos de la Selva", "Horacio Quiroga",
     "Cierta vez las víboras dieron un gran baile. Invitaron a las ranas y los sapos, a los flamencos, y a los yacarés y los pescados. Los pescados, como no caminan, no pudieron bailar; pero siendo el baile a la orilla del río los pescados estaban asomados a la arena.",
     "Infantil", 0.0, 1234, 312, 4.5, 30),
]


def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    # Primero borrar los 4 libros semilla para evitar duplicados
    cursor.execute("DELETE FROM reviews")
    cursor.execute("DELETE FROM books")
    conn.commit()
    print("Libros anteriores eliminados.")

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for book in BOOKS:
        title, author, content, category, price, views, likes, rating, reviews = book

        # Seleccionar portada basada en la categoría
        cat_covers = COVERS.get(category, list(COVERS.values())[0])
        cover_url = cat_covers[inserted % len(cat_covers)]

        cursor.execute(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url,
                               pdf_path, views, likes, average_rating, total_reviews, published, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """,
            (title, author, content, category, price, cover_url,
             None, views, likes, rating, reviews, now),
        )
        inserted += 1

        if inserted % 10 == 0:
            conn.commit()
            print(f"  ... {inserted} libros insertados")

    conn.commit()
    conn.close()

    # Contar por categoría
    categories = {}
    for b in BOOKS:
        cat = b[3]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n{'='*50}")
    print(f"✅ Total: {inserted} libros insertados exitosamente")
    print(f"{'='*50}")
    for cat, count in sorted(categories.items()):
        print(f"  📚 {cat}: {count} libros")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
