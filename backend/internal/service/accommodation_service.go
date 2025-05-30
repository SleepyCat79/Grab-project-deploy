package service

import (
	"skeleton-internship-backend/internal/model"
	"skeleton-internship-backend/internal/repository"

	"github.com/google/uuid"
)

type AccommodationService interface {
	CreateAccommodation(accommodation *model.Accommodation) (string, error)
	GetByID(id string) (model.Accommodation, error)
}

type accommodationService struct {
	accommodationRepo repository.AccommodationRepository
}

func NewAccommodationService(
	accommodationRepo repository.AccommodationRepository,
) AccommodationService {
	return &accommodationService{
		accommodationRepo: accommodationRepo,
	}
}

func (s *accommodationService) CreateAccommodation(accommodation *model.Accommodation) (string, error) {
	// Generate UUID for accommodation
	accommodation.AccommodationID = uuid.New().String()

	// Begin transaction
	tx := s.accommodationRepo.(*repository.GormAccommodationRepository).DB.Begin()

	// Create accommodation
	if err := tx.Create(accommodation).Error; err != nil {
		tx.Rollback()
		return "", err
	}

	// Commit transaction
	err := tx.Commit().Error
	if err != nil {
		return "", err
	}
	return accommodation.AccommodationID, nil
}

func (s *accommodationService) GetByID(id string) (model.Accommodation, error) {
	return s.accommodationRepo.GetByID(id)
}
