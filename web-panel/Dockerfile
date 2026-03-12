FROM nginx:alpine

# Copy files with proper permissions
COPY index.html /usr/share/nginx/html/index.html
COPY dashboard.html /usr/share/nginx/html/dashboard.html
COPY static/ /usr/share/nginx/html/static/

# Fix permissions - nginx runs as nginx user (uid 101)
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
