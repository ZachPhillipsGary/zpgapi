package models

import (
	"errors"
	"time"

	"github.com/jinzhu/gorm"

	"github.com/burke/nanomemo/supermemo"
)

type SpacedRepFact struct {
	FactData  supermemo.Fact `gorm:"embedded"`
	ID        uint64         `gorm:"primary_key;auto_increment" json:"id"`
	AuthorID  uint32         `gorm:"not null" json:"author_id"`
	Author    User           `json:"author"`
	CreatedAt time.Time      `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
	UpdatedAt time.Time      `gorm:"default:CURRENT_TIMESTAMP" json:"updated_at"`
}

func (p *SpacedRepFact) Prepare() {
	p.ID = 0
	p.Author = User{}
	p.CreatedAt = time.Now()
	p.UpdatedAt = time.Now()
	p.FactData = supermemo.Fact{}
}

func (p *SpacedRepFact) Validate() error {

	return nil
}

func (p *Post) DeleteFact(db *gorm.DB, fid uint64, uid uint32) (int64, error) {

	db = db.Debug().Model(&SpacedRepFact{}).Where("id = ? and author_id = ?", fid, uid).Take(&SpacedRepFact{}).Delete(&SpacedRepFact{})

	if db.Error != nil {
		if gorm.IsRecordNotFoundError(db.Error) {
			return 0, errors.New("Post not found")
		}
		return 0, db.Error
	}
	return db.RowsAffected, nil
}

func (p *SpacedRepFact) SaveFact(db *gorm.DB) (*SpacedRepFact, error) {
	var err error
	err = db.Debug().Model(&SpacedRepFact{}).Create(&p).Error
	if err != nil {
		return &SpacedRepFact{}, err
	}
	if p.ID != 0 {
		err = db.Debug().Model(&User{}).Where("id = ?", p.AuthorID).Take(&p.Author).Error
		if err != nil {
			return &SpacedRepFact{}, err
		}
	}
	return p, nil
}
