package dto

import (
	"skeleton-internship-backend/internal/model"
)

type TravelSuggestionResponse struct {
	IDs model.StringArray `json:"ids"`
}

type PlaceSuggestion struct {
	PlaceID       string            `json:"place_id"`
	DestinationID string            `json:"destination_id"`
	Name          string            `json:"name"`
	URL           string            `json:"url"`
	Address       string            `json:"address"`
	Duration      string            `json:"duration"`
	Type          string            `json:"type"`
	Images        model.ImageArray  `json:"images"`
	MainImage     string            `json:"main_image"`
	Price         float64           `json:"price"`
	Rating        float64           `json:"rating"`
	Description   string            `json:"description"`
	OpeningHours  string            `json:"opening_hours"`
	Reviews       model.StringArray `json:"reviews"`
	Categories    string            `json:"categories"`
	Unit          string            `json:"unit"`
}
type PlacesSuggestion struct {
	Places []PlaceSuggestion `json:"places"`
}

type RestaurantSuggestion struct {
	RestaurantID  string             `json:"restaurant_id"`
	DestinationID string             `json:"destination_id"`
	Name          string             `json:"name"`
	Address       string             `json:"address"`
	Rating        float64            `json:"rating"`
	Phone         string             `json:"phone"`
	PhotoURL      string             `json:"photo_url"`
	URL           string             `json:"url"`
	Location      model.Location     `json:"location"`
	Reviews       string             `json:"reviews"`
	Services      model.ServiceArray `json:"services"`
	IsDelivery    bool               `json:"is_delivery"`
	IsBooking     bool               `json:"is_booking"`
	IsOpening     bool               `json:"is_opening"`
	PriceRange    string             `json:"price_range"`
	Description   string             `json:"description"`
	Cuisines      string             `json:"cuisines"`
	OpeningHours  string             `json:"opening_hours"`
}

type RestaurantsSuggestion struct {
	Restaurants []RestaurantSuggestion `json:"restaurants"`
}

type AccommodationSuggestion struct {
	AccommodationID string              `json:"accommodation_id"`
	DestinationID   string              `json:"destination_id"`
	Name            string              `json:"name"`
	Location        string              `json:"location"`
	City            string              `json:"city"`
	Price           float64             `json:"price"`
	Rating          float64             `json:"rating"`
	Description     string              `json:"description"`
	Link            string              `json:"booking_link"`
	Images          model.ImageArray    `json:"image_url"`
	RoomTypes       model.RoomTypeArray `json:"room_types"`
	RoomInfo        string              `json:"room_info"`
	Unit            string              `json:"unit"`
	TaxInfo         string              `json:"tax_info"`
	ElderlyFriendly bool                `json:"elderly_friendly"`
}

type AccommodationsSuggestion struct {
	Accommodations []AccommodationSuggestion `json:"accommodations"`
}

type TripSuggestionRequest struct {
	DestinationID string                   `json:"destination_id"`
	Accommodation AccommodationsSuggestion `json:"accommodation"`
	Places        PlacesSuggestion         `json:"places"`
	Restaurants   RestaurantsSuggestion    `json:"restaurants"`
}

type SuggestWithIDAndType struct {
	Name string `json:"name"`
	Type string `json:"type"`
	Args string `json:"args"`
	ID   string `json:"id"`
}

type SuggestWithCommentRequest struct {
	TravelPreference model.TravelPreference `json:"travel_preference"`
	Activity         Activity               `json:"activity"`
}

type SuggestWithCommentResponse struct {
	SuggestionType string     `json:"suggestion_type"`
	SuggestionList []Activity `json:"suggestion_list"`
}

type ActivityDetail struct {
	ID             string            `json:"id"`
	Type           string            `json:"type"`
	Name           string            `json:"name"`
	Address        string            `json:"address"`
	Rating         float64           `json:"rating"`
	Price          float64           `json:"price"`
	Description    string            `json:"description"`
	ImageURLs      model.StringArray `json:"image_urls"`
	OpeningHours   string            `json:"opening_hours"`
	AdditionalInfo string            `json:"additional_info"`
	Location       string            `json:"location"`
	URL            string            `json:"url"`
}

func (a AccommodationSuggestion) ToActivityDetail() ActivityDetail {
	var images model.StringArray
	for _, image := range a.Images {
		images = append(images, image.URL)
	}

	activityDetail := ActivityDetail{
		ID:             a.AccommodationID,
		Type:           "accommodation",
		Name:           a.Name,
		Address:        a.Location,
		Rating:         a.Rating,
		Price:          a.Price,
		Description:    a.Description,
		ImageURLs:      images,
		OpeningHours:   "",
		AdditionalInfo: a.TaxInfo,
		Location:       a.City,
		URL:            a.Link,
	}
	return activityDetail
}

func (r RestaurantSuggestion) ToActivityDetail() ActivityDetail {
	return ActivityDetail{
		ID:             r.RestaurantID,
		Type:           "restaurant",
		Name:           r.Name,
		Address:        r.Address,
		Rating:         r.Rating,
		Price:          0, // Price is not available in RestaurantSuggestion
		Description:    r.Description,
		ImageURLs:      model.StringArray{r.PhotoURL},
		OpeningHours:   r.OpeningHours,
		AdditionalInfo: "",
		Location:       r.DestinationID,
		URL:            r.URL,
	}
}

func (p PlaceSuggestion) ToActivityDetail() ActivityDetail {
	var images model.StringArray
	if p.MainImage != "" {
		images = append(images, p.MainImage)
	}
	for _, image := range p.Images {
		images = append(images, image.URL)
	}
	return ActivityDetail{
		ID:             p.PlaceID,
		Type:           "place",
		Name:           p.Name,
		Address:        p.Address,
		Rating:         p.Rating,
		Price:          p.Price,
		Description:    p.Description,
		ImageURLs:      images,
		OpeningHours:   p.OpeningHours,
		AdditionalInfo: "",
		Location:       "",
		URL:            p.URL,
	}
}
