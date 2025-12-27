export namespace controller {

	export class PublicFanState {
	    Name: string;
	    Mode: string;
	    ManualSpeed: number;
	    TargetSpeedPercent: number;
	    ReadSpeedPercent: number;

	    static createFrom(source: any = {}) {
	        return new PublicFanState(source);
	    }

	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Name = source["Name"];
	        this.Mode = source["Mode"];
	        this.ManualSpeed = source["ManualSpeed"];
	        this.TargetSpeedPercent = source["TargetSpeedPercent"];
	        this.ReadSpeedPercent = source["ReadSpeedPercent"];
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
	    lastConfigPath: string;
	    language: string;
	    autoStart: boolean;
	    criticalTemp: number;
	    safetyAction: string;

	    static createFrom(source: any = {}) {
	        return new Settings(source);
	    }

	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.lastConfigPath = source["lastConfigPath"];
	        this.language = source["language"];
	        this.autoStart = source["autoStart"];
	        this.criticalTemp = source["criticalTemp"];
	        this.safetyAction = source["safetyAction"];
	    }
	}

}
