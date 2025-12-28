//go:build windows

package main

import (
	"embed"
	"log"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/menu"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	// Create an instance of the app structure
	app := NewApp()

	appMenu := menu.NewMenu()
	// TODO: Add application menu here

	sysTray := menu.NewMenu()
	sysTray.Add("Show").OnClick(func(ctx *menu.CallbackData) {
		runtime.Show(app.ctx)
	})
	sysTray.Add("Quit").OnClick(func(ctx *menu.CallbackData) {
		runtime.Quit(app.ctx)
	})

	// Create application with options
	err := wails.Run(&options.App{
		Title:  "VortECIO-Go",
		Width:  720,
		Height: 540,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		Menu:             appMenu,
		BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},
		OnStartup:        app.startup,
		OnShutdown:       app.shutdown,
		Bind: []interface{}{
			app,
		},
		SysTray: sysTray,
		// TODO: Implement dynamic tray icon with temperature updates
	})

	if err != nil {
		log.Fatal(err)
	}
}
