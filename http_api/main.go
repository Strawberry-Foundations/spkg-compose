package main

import (
	"fmt"
	"http_api/config"
	"http_api/routes"
	"log"
	"net/http"
)

func main() {
	config.LoadConfig("../data/config.yml")

	http.HandleFunc("/upload", upload.Handler)

	address := config.API.Address
	port := config.API.Port
	log.Printf("Starting server at %s:%d\n", address, port)
	log.Fatal(http.ListenAndServe(fmt.Sprintf("%s:%d", address, port), nil))
}
