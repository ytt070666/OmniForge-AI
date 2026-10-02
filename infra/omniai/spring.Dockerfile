FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY services/omniai_enterprise_spring/pom.xml .
COPY services/omniai_enterprise_spring/src src
RUN mvn -q -DskipTests package
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/enterprise-connector-0.1.0.jar app.jar
EXPOSE 8096
ENTRYPOINT ["java", "-jar", "/app/app.jar", "--server.port=8096"]
