la base de datos se llama: contabilidad_personal
el usuario master es: xavier y la contraseña: 1234

---- variables de entorno estas no debo usar para desplegar ----
---- debo sólo cambiar la url database por local con las credenciales ---
export DATABASE_URL='postgresql://postgres:HBcydfmgMctKDZoFFqXfTragVVWRPJXj@postgres.railway.internal:5432/railway' 
export SECRET_KEY='b90a493444a04c2013fb965eed73962e' 
export JWT_SECRET_KEY='b90a493444a04c2013fb965eed73962e'
export ENCRYPTION_KEY='yxZZI9aulu-l-ErwCUr5AI4FLKQWrrCAxVBoqqgCVVY='



PARA ENTRAR A LA B.D 
psql -d contabilidad_personal -U xavier

PARA CONSULTAR TABLAS
psql -d contabilidad_personal -U xavier
SELECT * FROM ingreso;

PARA CONSULTAR LOS USUARIOS REGISTRADOS:
psql -d contabilidad_personal -U xavier
SELECT * FROM "user";



PARA SALIR
\q

VACIAR REGISTROS DE LA TABLA:
psql -d contabilidad_personal -U xavier
TRUNCATE TABLE ingreso;


PARA ENTRAR A EL ENVIORNMENT EN PYTHON
deactivate
source venv/bin/activate


PARA BORRAR UN INGRESO DE LA TABLA
psql -d contabilidad_personal -U xavier
SELECT * FROM ingreso;    //LISTA LOS REGISTROS DE LA TABLA INGRESO
DELETE FROM ingresos WHERE id = 10;     //BORRA UN REGISTRO ESPECÍFICO
SELECT * FROM ingreso;       //VERIFICA QUE EL REGISTRO SE HA BORRADO


PARA DESBLOQUEARLO SI SE LE BLOQUEO POR NUMERO DE INTENTOS:
psql -d contabilidad_personal -U xavier
UPDATE "user" SET failed_attempts = 0 WHERE username = 'pruebas';

LUEGO PARA CAMBIAR SU CONTRASEÑA:
psql -d contabilidad_personal -U xavier
UPDATE "user" SET password = crypt('hola', gen_salt('bf')) WHERE username = 'pruebas';


VACIAR REGISTROS DE UNA TABLA DE UN USUARIO ESPECÍFICO !
SELECT * FROM "user"; // así veo todos los usuarios
SELECT id FROM "user" WHERE username = 'pruebas'; // ASI DEBO OBTENER EL USER ID DEL USUARIO
DELETE FROM egreso WHERE user_id = 5;  //ASÍ BORRO LOS REGISTROS DE ESA TABLA


.