package upload

import (
	"encoding/json"
	"fmt"
	"http_api/config"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type PackageIndex map[string]Package

type Package struct {
	BinpkgPath string `json:"binpkg_path"`
}

var index PackageIndex
var dataDir = "../data"
var initDir = "../"

func init() {
	indexPath := filepath.Join(dataDir, "index.json")
	indexData, err := os.ReadFile(indexPath)
	if err != nil {
		log.Fatalf("Failed to read index file: %v", err)
	}
	err = json.Unmarshal(indexData, &index)
	if err != nil {
		log.Fatalf("Failed to unmarshal index: %v", err)
	}
}

func Handler(w http.ResponseWriter, r *http.Request) {
	authHeader := r.Header.Get("Authorization")
	packageName := r.Header.Get("Package")

	if !isValidToken(authHeader) {
		log.Println("Client authenticated with an invalid token")
		http.Error(w, "Forbidden", http.StatusForbidden)
		return
	}

	file, fileHeader, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "No file part", http.StatusBadRequest)
		return
	}
	defer func(file multipart.File) {
		err := file.Close()
		if err != nil {

		}
	}(file)

	if fileHeader.Filename == "" {
		http.Error(w, "No selected file", http.StatusBadRequest)
		return
	}

	packageInfo, ok := index[packageName]
	if !ok {
		http.Error(w, "Package not found", http.StatusNotFound)
		return
	}

	destPath := filepath.Join(initDir, "local_repo", packageInfo.BinpkgPath, fileHeader.Filename)
	out, err := os.Create(destPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to save file: %v", err), http.StatusInternalServerError)
		return
	}
	defer func(out *os.File) {
		err := out.Close()
		if err != nil {

		}
	}(out)

	fileBytes, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to read file: %v", err), http.StatusInternalServerError)
		return
	}

	_, err = out.Write(fileBytes)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to write file: %v", err), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	_, err = fmt.Fprintf(w, "Binpkg for package '%s' uploaded successfully (%s)", packageName, fileHeader.Filename)
	if err != nil {
		return
	}
}

func isValidToken(authHeader string) bool {
	if !strings.HasPrefix(authHeader, "Bearer ") {
		return false
	}
	token := strings.TrimPrefix(authHeader, "Bearer ")
	for _, allowedToken := range config.API.AllowedTokens {
		if token == allowedToken {
			return true
		}
	}
	return false
}
