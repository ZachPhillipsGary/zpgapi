package controllers

import (
	"net/http"

	"github.com/zachphillipsgary/fullstack/zpgapi/responses"
)

func (server *Server) Home(w http.ResponseWriter, r *http.Request) {
	responses.JSON(w, http.StatusOK, "Welcome To This Awesome API")

}
