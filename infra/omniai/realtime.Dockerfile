FROM golang:1.26 AS build
WORKDIR /src
COPY services/omniai_realtime_go/go.mod services/omniai_realtime_go/go.sum ./
COPY services/omniai_realtime_go/main.go ./
RUN go mod download && CGO_ENABLED=0 go build -trimpath -o /out/realtime .
FROM gcr.io/distroless/static-debian12
COPY --from=build /out/realtime /realtime
EXPOSE 8092
ENTRYPOINT ["/realtime"]
