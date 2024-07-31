package config

import (
	"gopkg.in/yaml.v3"
	"log"
	"os"
)

type Config struct {
	RepoAPI RepoAPI `yaml:"repo_http_api"`
}

type RepoAPI struct {
	Address       string   `yaml:"address"`
	Port          int      `yaml:"port"`
	AllowedTokens []string `yaml:"allowed_tokens"`
}

var API RepoAPI

func LoadConfig(path string) {
	var config Config

	data, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("Failed to read config file: %v", err)
	}
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		log.Fatalf("Failed to unmarshal config: %v", err)
	}

	API = config.RepoAPI
}
