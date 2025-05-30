package model

import (
	"time"
)

// TripRestaurant maps to the "trip_restaurants" table.
type TripRestaurant struct {
	TripRestaurantID  string     `gorm:"type:char(36);primaryKey" json:"trip_restaurant_id"`
	TripDestinationID string     `gorm:"type:char(36);column:trip_destination_id;not null" json:"trip_destination_id"`
	RestaurantID      string     `gorm:"type:char(36);column:restaurant_id;" json:"restaurant_id"`
	MealDate          *time.Time `gorm:"column:meal_date" json:"meal_date,omitempty"`
	StartTime         *time.Time `gorm:"column:start_time" json:"start_time,omitempty"`
	EndTime           *time.Time `gorm:"column:end_time" json:"end_time,omitempty"`
	ReservationInfo   string     `gorm:"column:reservation_info;size:255" json:"reservation_info"`
	Notes             string     `gorm:"column:notes" json:"notes"`
	PriceAIEstimate   float64    `gorm:"column:price_ai_estimate" json:"price_ai_estimate"`

	// Associations with proper GORM foreign key definitions
	TripDestination *TripDestination `json:"trip_destination,omitempty"`
	Restaurant      *Restaurant      `json:"restaurant,omitempty"`
	Comments        []Comment        `gorm:"foreignKey:TripRestaurantID" json:"comments,omitempty"`
}
