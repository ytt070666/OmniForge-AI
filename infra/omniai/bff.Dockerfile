FROM node:22-alpine AS build
WORKDIR /app
COPY services/omniai_bff_nest/package.json services/omniai_bff_nest/package-lock.json services/omniai_bff_nest/tsconfig.json ./
RUN npm ci
COPY services/omniai_bff_nest/src src
RUN npm run build
FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/package.json /app/package-lock.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist dist
EXPOSE 8093
CMD ["node", "dist/main.js"]
