FROM alpine:3.18 AS mc-download

RUN apk add --no-cache wget \
 && wget https://dl.min.io/client/mc/release/linux-amd64/mc \
 && chmod +x mc

# Se puede importar más de una imagen en un docker file
FROM minio/minio

# Copiamos el binario mc
COPY --from=mc-download /mc /usr/bin/mc

COPY docker-entrypoint.sh /usr/bin/docker-entrypoint.sh
RUN chmod +x /usr/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/bin/docker-entrypoint.sh"]

CMD ["server", "/data", "--console-address", ":9001"]
