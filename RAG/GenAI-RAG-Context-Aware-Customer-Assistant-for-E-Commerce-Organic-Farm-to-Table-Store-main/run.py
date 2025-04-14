from server.app import create_app
from server.website import Website
from server.backend import Backend_Api
from json import load
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    try:
        config = load(open('config.json', 'r'))
        site_config = config['site_config']
        
        # Create the app without registering routes
        app = create_app(config, register_routes=False)
        
        # Register Website routes
        site = Website(app)
        for route, options in site.routes.items():
            app.add_url_rule(
                route,
                view_func=options['function'],
                methods=options['methods'],
            )

        # Register Backend_Api routes
        backend_api = Backend_Api(app, config)
        for route, options in backend_api.routes.items():
            app.add_url_rule(
                route,
                view_func=options['function'],
                methods=options['methods'],
            )

        # Log the routes
        logging.info("Registered routes:")
        for rule in app.url_map.iter_rules():
            logging.info(f"{rule.endpoint}: {rule.methods} {rule.rule}")

        # Run the app
        logging.info(f"Starting server on port {site_config['port']}")
        app.run(**site_config)
        
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
    finally:
        logging.info("Server shutting down.")
