package repository

import (
	"skeleton-internship-backend/internal/model"
	"time"

	"gorm.io/gorm"
)

// TripRepository defines data access methods for the Trip entity.
type TripRepository interface {
	GetByID(tripID string) (model.Trip, error)
	Create(trip *model.Trip) error
	Update(trip *model.Trip) error
	Delete(tripID string) error
	GetByUserID(userID string) ([]model.Trip, error)
	GetAll() ([]model.Trip, error)
	GetWithAssociations(tripID string) (model.Trip, error)
	GetAllWithAssociations() ([]model.Trip, error)
	GetByUserIDWithAssociation(userID string) ([]model.Trip, error)
}

// GormTripRepository implements TripRepository using GORM.
type GormTripRepository struct {
	DB *gorm.DB
}

// NewTripRepository returns a new GORM-based Trip repository.
func NewTripRepository(db *gorm.DB) TripRepository {
	return &GormTripRepository{DB: db}
}

// Create saves a new Trip record.
func (r *GormTripRepository) Create(trip *model.Trip) error {
	now := time.Now()
	trip.CreatedAt = now
	trip.UpdatedAt = now
	return r.DB.Create(trip).Error
}

// GetByID retrieves a Trip by its ID.
func (r *GormTripRepository) GetByID(tripID string) (model.Trip, error) {
	var trip model.Trip
	if err := r.DB.First(&trip, "trip_id = ?", tripID).Error; err != nil {
		return model.Trip{}, err
	}
	return trip, nil
}

// Update modifies an existing Trip record.
func (r *GormTripRepository) Update(trip *model.Trip) error {
	trip.UpdatedAt = time.Now()
	return r.DB.Model(&model.Trip{}).Where("trip_id = ?", trip.TripID).Updates(trip).Error
}

// Delete removes a Trip record by its ID.
func (r *GormTripRepository) Delete(tripID string) error {
	return r.DB.Delete(&model.Trip{}, "trip_id = ?", tripID).Error
}

// GetByUserID retrieves all Trip records associated with a specific UserID.
func (r *GormTripRepository) GetByUserID(userID string) ([]model.Trip, error) {
	var trips []model.Trip
	if err := r.DB.Where("user_id = ?", userID).Find(&trips).Error; err != nil {
		return nil, err
	}
	return trips, nil
}

// GetAll retrieves all Trip records.
func (r *GormTripRepository) GetAll() ([]model.Trip, error) {
	var trips []model.Trip
	if err := r.DB.Find(&trips).Error; err != nil {
		return nil, err
	}
	return trips, nil
}

// GetWithAssociations retrieves a Trip by its ID with associated records.
func (r *GormTripRepository) GetWithAssociations(tripID string) (model.Trip, error) {
	var trip model.Trip
	if err := r.DB.Preload("TripDestinations").First(&trip, "trip_id = ?", tripID).Error; err != nil {
		return trip, err
	}
	return trip, nil
}

// GetAllWithAssociations retrieves all Trip records with associated records.
func (r *GormTripRepository) GetAllWithAssociations() ([]model.Trip, error) {
	var trips []model.Trip
	if err := r.DB.Preload("TripDestinations").Find(&trips).Error; err != nil {
		return nil, err
	}
	return trips, nil
}

// GetByUserIDWithAssociation retrieves all Trip records associated with a specific UserID with associated records.
func (r *GormTripRepository) GetByUserIDWithAssociation(userID string) ([]model.Trip, error) {
	var trips []model.Trip
	if err := r.DB.Preload("TripDestinations").Where("user_id = ?", userID).Find(&trips).Error; err != nil {
		return nil, err
	}

	for i := range trips {
		for j := range trips[i].TripDestinations {
			tripDestinationID := trips[i].TripDestinations[j].TripDestinationID

			// Get TripAccommodations
			var accommodations []model.TripAccommodation
			if err := r.DB.Where("trip_destination_id = ?", tripDestinationID).Find(&accommodations).Error; err != nil {
				return nil, err
			}
			trips[i].TripDestinations[j].Accommodations = accommodations

			// Get TripRestaurants
			var restaurants []model.TripRestaurant
			if err := r.DB.Where("trip_destination_id = ?", tripDestinationID).Find(&restaurants).Error; err != nil {
				return nil, err
			}
			trips[i].TripDestinations[j].Restaurants = restaurants

			// Get TripPlaces
			var places []model.TripPlace
			if err := r.DB.Where("trip_destination_id = ?", tripDestinationID).Find(&places).Error; err != nil {
				return nil, err
			}
			trips[i].TripDestinations[j].Places = places
		}
	}

	return trips, nil
}
