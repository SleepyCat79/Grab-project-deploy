package main

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	"go.uber.org/fx"

	"skeleton-internship-backend/config"
	"skeleton-internship-backend/database"
	_ "skeleton-internship-backend/docs" // This will be created by swag
	"skeleton-internship-backend/internal/controller"
	"skeleton-internship-backend/internal/logger"
	"skeleton-internship-backend/internal/repository"
	"skeleton-internship-backend/internal/service"
)

// @title           Travel Planning API
// @version         1.0
// @description     A modern RESTful API for managing travel plans, including trips, destinations, accommodations, places, and restaurants.
// @termsOfService  http://swagger.io/terms/

// @contact.name   API Support Team
// @contact.url    http://www.example.com/support
// @contact.email  support@example.com

// @license.name  MIT
// @license.url   https://opensource.org/licenses/MIT

// @host      localhost:8080
// @BasePath  /api/v1
// @schemes   http https

// @tag.name         auth
// @tag.description  Operations about login and register
// @tag.docs.url     http://example.com/docs/auth
// @tag.docs.description Detailed information about auth operations

// @tag.name         health
// @tag.description  API health check operations

// @tag.name         suggest
// @tag.description  Operations about travel suggestions
// @tag.docs.url     http://example.com/docs/suggest
// @tag.docs.description Detailed information about suggestion operations

// @tag.name         trip
// @tag.description  Operations about trips and travel plans
// @tag.docs.url     http://example.com/docs/trip
// @tag.docs.description Detailed information about trip operations

// @tag.name         comment
// @tag.description  Operations about comments
// @tag.docs.url     http://example.com/docs/comment
// @tag.docs.description Detailed information about comment operations

// @tag.name         InsertData
// @tag.description  Operations for importing data from CSV files

// @tag.name         expense
// @tag.description  Operations about trip expenses and expense splitting
// @tag.docs.url     http://example.com/docs/expense
// @tag.docs.description Detailed information about expense operations

// @securityDefinitions.apikey Bearer
// @in header
// @name Authorization
// @description Enter the token with the `Bearer: ` prefix, e.g. "Bearer abcde12345".

func main() {
	app := fx.New(
		fx.Provide(
			NewConfig,
			database.NewDB,
			NewGinEngine,
			repository.NewRepository,
			repository.NewUserRepository,
			repository.NewPlaceRepository,
			repository.NewRestaurantRepository,
			repository.NewAccommodationRepository,
			repository.NewTripRepository,
			repository.NewTripDestinationRepository,
			repository.NewTripAccommodationRepository,
			repository.NewTripPlaceRepository,
			repository.NewTripRestaurantRepository,
			repository.NewCommentRepository,
			repository.NewTravelPreferenceRepository,
			repository.NewExpenseRepository,
			repository.NewExpenseUserRepository,
			service.NewService,
			service.NewAuthService,
			service.NewTripService,
			service.NewSuggestService,
			service.NewInsertDataService,
			service.NewWebSocketService,
			service.NewCommentService,
			service.NewExpenseService,
			controller.NewController,
			controller.NewAuthController,
			controller.NewTripController,
			controller.NewSuggestController,
			controller.NewInsertDataController,
			controller.NewWebSocketController,
			controller.NewCommentController,
			controller.NewExpenseController,
		),
		fx.StartTimeout(1*time.Minute),
		fx.Invoke(RegisterRoutes),
	)

	app.Run()
}

func NewConfig() (*config.Config, error) {
	return config.NewConfig()
}

func NewGinEngine() *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())

	// Configure CORS
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"}, // Add your frontend URLs
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Add swagger route
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	return r
}

func RegisterRoutes(
	lifecycle fx.Lifecycle,
	router *gin.Engine,
	cfg *config.Config,
	controller *controller.Controller,
	auth_controller *controller.AuthController,
	suggest_controller *controller.SuggestController,
	trip_controller *controller.TripController,
	comment_controller *controller.CommentController,
	webSocketController *controller.WebSocketController,
	insertDataController *controller.InsertDataController,
	expense_controller *controller.ExpenseController,
	insertDataService service.InsertDataService,
) {
	controller.RegisterRoutes(router)
	auth_controller.RegisterRoutes(router)
	suggest_controller.RegisterRoutes(router)
	trip_controller.RegisterRoutes(router)
	comment_controller.RegisterRoutes(router)
	insertDataController.RegisterRoutes(router)
	webSocketController.RegisterRoutes(router)
	expense_controller.RegisterRoutes(router)

	logger.Init()

	server := &http.Server{
		Addr:    ":" + cfg.Server.Port,
		Handler: router,
	}

	lifecycle.Append(fx.Hook{
		OnStart: func(ctx context.Context) error {
			log.Info().Msgf("Starting server on port %s", cfg.Server.Port)

			// // Insert destination data
			// err := insertDataService.InsertDestinationData("./mockdata/city_processed.csv")
			// if err != nil {
			// 	log.Fatal().Err(err).Msg("Failed to import data from CSV")
			// }
			// log.Info().Msg("Destination data imported successfully")
			// // Insert hotel data
			// err = insertDataService.InsertHotelData("./mockdata/hotel_processed.csv")
			// if err != nil {
			// 	log.Fatal().Err(err).Msg("Failed to import data from CSV")
			// }
			// log.Info().Msg("Hotel data imported successfully")
			// // Insert place data
			// err = insertDataService.InsertPlaceData("./mockdata/place_processed.csv")
			// if err != nil {
			// 	log.Fatal().Err(err).Msg("Failed to import data from CSV")
			// }
			// log.Info().Msg("Place data imported successfully")
			// // Insert restaurant data
			// err = insertDataService.InsertRestaurantData("./mockdata/fnb_processed.csv")
			// if err != nil {
			// 	log.Fatal().Err(err).Msg("Failed to import data from CSV")
			// }
			// log.Info().Msg("Restaurant data imported successfully")

			go func() {
				if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
					log.Fatal().Err(err).Msg("Failed to start server")
				}
			}()
			return nil
		},
		OnStop: func(ctx context.Context) error {
			log.Info().Msg("Shutting down server")
			return server.Shutdown(ctx)
		},
	})
}
