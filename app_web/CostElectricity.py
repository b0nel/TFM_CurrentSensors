import requests
import json


class costElectricity:
    """
    Class to get the price of electricity in Spain
    """
    def __init__(self):
        self.url_complete   = 'https://api.preciodelaluz.org/v1/prices/all?zone=PCB'
        self.url_average    = 'https://api.preciodelaluz.org/v1/prices/avg?zone=PCB'
        self.url_max        = 'https://api.preciodelaluz.org/v1/prices/max?zone=PCB'
        self.url_min        = 'https://api.preciodelaluz.org/v1/prices/min?zone=PCB'
        self.url_current    = 'https://api.preciodelaluz.org/v1/prices/now?zone=PCB'
        self.url_eco        = 'https://api.preciodelaluz.org/v1/prices/cheapests?zone=PCB&n='
        self.complete_data  = None
        self.average_data   = None
        self.max_data       = None
        self.min_data       = None
        self.current_data   = None

    
    def get_url_data(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            print("Error  getting data from " + url)
            return self.current_data


    def load_complete_data(self):
        self.complete_data = self.get_url_data(self.url_complete)

    def load_average_data(self):
        self.average_data = self.get_url_data(self.url_average)
    
    def load_max_data(self):
        self.max_data = self.get_url_data(self.url_max)
    
    def load_min_data(self):
        self.min_data = self.get_url_data(self.url_min)
    
    def load_current_data(self):
        self.current_data = self.get_url_data(self.url_current)

    def update_everything(self):
        self.load_complete_data()
        self.load_average_data()
        self.load_max_data()
        self.load_min_data()
        self.load_current_data()

    """ Returns a list of the n cheapest prices in the day """
    def get_eco_price(self, n):
        return self.get_url_data(self.url_eco + str(n))

        


def main():
    cost_electricity = costElectricity()
    cost_electricity.update_everything()
    for franja, datos in cost_electricity.complete_data.items():
        print("En la franja horaria " + franja + " el precio es de " + str(datos["price"] / 1000) + " euros por kWh")
    print("El precio actual es de " + str(cost_electricity.current_data["price"] / 1000) + " euros por kWh")
    print("El precio medio es de " + str(cost_electricity.average_data["price"] / 1000) + " euros por kWh")
    print("El precio máximo es de " + str(cost_electricity.max_data["price"] / 1000) + " euros por kWh")
    print("El precio mínimo es de " + str(cost_electricity.min_data["price"] / 1000) + " euros por kWh")
    print("Los 5 precios más económicos son:")
    for franja in cost_electricity.get_eco_price(5):
        print(str(franja["price"] / 1000) + " euros por kWh en la franja horaria " + franja["hour"])
    
if __name__ == '__main__':
    main()
