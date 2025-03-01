FROM nginx:alpine

# Copy the client files
COPY . /usr/share/nginx/html/

# Copy a custom nginx config if needed
COPY nginx.conf /etc/nginx/conf.d/default.conf 