export namespace controller {

	export class PublicFanState {
	    name: string;
	    mode: string;
	    manualSpeed: number;
	    targetSpeedPercent: number;
	    readSpeedPercent: number;
	    currentRpm: number;
	    temperatureThresholds: models.TemperatureThreshold[];

	    static createFrom(source: any = {}) {
	        return new PublicFanState(source);
	    }

	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.mode = source["mode"];
	        this.manualSpeed = source["manualSpeed"];
	        this.targetSpeedPercent = source["targetSpeedPercent"];
	        this.readSpeedPercent = source["readSpeedPercent"];
	        this.currentRpm = source["currentRpm"];
	        this.temperatureThresholds = this.convertValues(source["temperatureThresholds"], models.TemperatureThreshold);
	    }

		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class PublicState {
	    SystemTemp: number;
	    GpuTemp: number;
	    Fans: PublicFanState[];
	    ModelName: string;

	    static createFrom(source: any = {}) {
	        return new PublicState(source);
	    }

	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.SystemTemp = source["SystemTemp"];
	        this.GpuTemp = source["GpuTemp"];
	        this.Fans = this.convertValues(source["Fans"], PublicFanState);
	        this.ModelName = source["ModelName"];
	    }

		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

export namespace models {

	export class Settings {
	    language: string;
	    autoStart: boolean;
	    lastConfigPath: string;
	    criticalTemp: number;
	    safetyAction: string;
	    enableCriticalTempRecovery: boolean;
	    criticalTempRecoveryDelta: number;

	    static createFrom(source: any = {}) {
	        return new Settings(source);
	    }

	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.language = source["language"];
	        this.autoStart = source["autoStart"];
	        this.lastConfigPath = source["lastConfigPath"];
	        this.criticalTemp = source["criticalTemp"];
	        this.safetyAction = source["safetyAction"];
	        this.enableCriticalTempRecovery = source["enableCriticalTempRecovery"];
	        this.criticalTempRecoveryDelta = source["criticalTempRecoveryDelta"];
	    }
	}
	export class TemperatureThreshold {
	    UpThreshold: number;
	    DownThreshold: number;
	    FanSpeed: number;

	    static createFrom(source: any = {}) {
	        return new TemperatureThreshold(source);
	    }

	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.UpThreshold = source["UpThreshold"];
	        this.DownThreshold = source["DownThreshold"];
	        this.FanSpeed = source["FanSpeed"];
	    }
	}

}
