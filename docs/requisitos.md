# Jenkins AIOps: qué hace y para qué sirve

Este documento explica el proyecto en lenguaje simple, sin términos técnicos,
para cualquier persona que quiera entender qué hace el sistema.

## ¿Qué problema resuelve?

Cuando un equipo de desarrollo usa Jenkins para compilar y desplegar su
software, es normal que algunas ejecuciones ("builds") fallen. Hoy en día,
alguien tiene que entrar manualmente, leer un log larguísimo y tratar de
entender qué salió mal. Eso toma tiempo y, muchas veces, el mismo error se
repite y se vuelve a investigar desde cero.

Jenkins AIOps hace ese trabajo automáticamente: revisa cada build que falla,
usa inteligencia artificial para explicar qué pasó y en qué archivo, y
recuerda los errores ya vistos para no volver a analizarlos desde cero.

## ¿Qué hace, en la práctica?

1. **Vigila Jenkins.** Cada vez que una build termina, el sistema se entera
   (Jenkins le avisa, o el sistema pregunta periódicamente por si acaso).

2. **Si la build fue exitosa, no hace nada especial** — solo la registra.
   No gasta tiempo ni recursos de inteligencia artificial en algo que
   funcionó bien.

3. **Si la build falló**, el sistema:
   - Primero revisa si el error ya lo vio antes (con reglas simples o
     comparando el log con fallos anteriores). Si es un error conocido,
     reutiliza la explicación ya generada — es instantáneo y gratis.
   - Si es un error nuevo, lo manda a analizar con un modelo de
     inteligencia artificial, que lee el log y devuelve:
     - **Categoría** del problema (por ejemplo, "error de configuración").
     - **Causa raíz**: qué pasó, explicado en palabras simples.
     - **Archivo afectado**: en qué archivo del proyecto está el problema,
       si se puede identificar.
     - **Confianza**: qué tan seguro está el sistema de su propio
       diagnóstico.
     - **Recomendación**: qué hacer para solucionarlo.
   - Ese diagnóstico se guarda, así que si el mismo error vuelve a pasar,
     ya no hace falta volver a preguntarle a la inteligencia artificial.

4. **Muestra todo en un panel web** (como un tablero de control):
   - Cada build aparece como una tarjeta con su estado (éxito, fallo,
     inestable), el diagnóstico y una recomendación.
   - El panel se actualiza solo cada 15 segundos, sin que la persona tenga
     que recargar la página.
   - Se puede filtrar por estado, por proyecto (job), por categoría del
     error o por fecha, para encontrar rápido lo que se busca.
   - Al entrar al detalle de una build se ve el log completo, con las
     palabras clave de error resaltadas en color (`ERROR`, `WARN`,
     `Exception`, `Caused by`) para que sean fáciles de detectar a simple
     vista.

5. **Permite conversar sobre el fallo.** Desde el detalle de una build hay
   un chat: se le puede preguntar a la inteligencia artificial cosas como
   "¿por qué falló este paso?" o "¿cómo lo soluciono?", y responde basándose
   en el log real de esa build.

6. **Aprende con el feedback de las personas.** Cada diagnóstico tiene
   botones de "👍 útil" / "👎 no útil". Si varias personas marcan un
   diagnóstico como no útil, el sistema deja de reutilizarlo automáticamente
   y vuelve a analizarlo con más cuidado la próxima vez.

## ¿Qué necesita para funcionar?

- **Jenkins**, ya en uso por el equipo (no lo reemplaza, se conecta a él).
- **Un modelo de inteligencia artificial** que lea los logs y genere las
  explicaciones. Puede ser uno que corre en la propia infraestructura de la
  empresa (sin mandar datos afuera) o uno de un proveedor externo.
- **Un lugar donde correr el sistema** (un servidor o una nube), levantado
  con Docker — no requiere instalación manual paso a paso.

## Lo que este sistema NO hace

- No corrige el código automáticamente ni hace commits — solo diagnostica y
  recomienda; la persona sigue siendo quien decide y aplica el arreglo.
- No reemplaza a Jenkins ni cambia cómo se compilan o despliegan los
  proyectos.
- No envía el log completo a ningún lado fuera de lo configurado por el
  equipo — el modelo de inteligencia artificial que se use es una decisión
  explícita de configuración.
