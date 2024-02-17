
import csv
import glob
import os
import sys
import time
import pprint
from models.fuel_consumption_predictor import FuelConsumptionPredictor

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

from carla import VehicleLightState as vls

import argparse
import logging
from numpy import random

def get_actor_blueprints(world, filter, generation):
    bps = world.get_blueprint_library().filter(filter)

    if generation.lower() == "all":
        return bps

    # If the filter returns only one bp, we assume that this one needed
    # and therefore, we ignore the generation
    if len(bps) == 1:
        return bps

    try:
        int_generation = int(generation)
        # Check if generation is in available generations
        if int_generation in [1, 2]:
            bps = [x for x in bps if int(x.get_attribute('generation')) == int_generation]
            return bps
        else:
            print("   Warning! Actor Generation is not valid. No actor will be spawned.")
            return []
    except:
        print("   Warning! Actor Generation is not valid. No actor will be spawned.")
        return []


class GenerateTraffic():
    def __init__(self, host='127.0.0.1', port=2000, number_of_vehicles=30, number_of_walkers=10,
                 safe=True, filterv='vehicle.audi.*', generationv='All', filterw='walker.pedestrian.*',
                 generationw='2', tm_port=8000, asynch=False, hybrid=False, seed=None, seedw=0,
                 car_lights_on=False, hero=False, respawn=True, no_rendering=False):
        self.host = host
        self.port = port
        self.number_of_vehicles = number_of_vehicles
        self.number_of_walkers = number_of_walkers
        self.safe = safe
        self.filterv = filterv
        self.generationv = generationv
        self.filterw = filterw
        self.generationw = generationw
        self.tm_port = tm_port
        self.asynch = asynch
        self.hybrid = hybrid
        self.seed = seed
        self.seedw = seedw
        self.car_lights_on = car_lights_on
        self.hero = hero
        self.respawn = respawn
        self.no_rendering = no_rendering
        
    def start_traffic(self):
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

        vehicles_list = []
        walkers_list = []
        all_id = []
        client = carla.Client(self.host, self.port)
        client.set_timeout(10.0)
        synchronous_master = False
        random.seed(self.seed if self.seed is not None else int(time.time()))

        try:
            world = client.get_world()

            traffic_manager = client.get_trafficmanager(self.tm_port)
            traffic_manager.set_global_distance_to_leading_vehicle(2.5)
            if self.respawn:
                traffic_manager.set_respawn_dormant_vehicles(True)
            if self.hybrid:
                traffic_manager.set_hybrid_physics_mode(True)
                traffic_manager.set_hybrid_physics_radius(70.0)
            if self.seed is not None:
                traffic_manager.set_random_device_seed(self.seed)

            settings = world.get_settings()
            if not self.asynch:
                traffic_manager.set_synchronous_mode(True)
                if not settings.synchronous_mode:
                    synchronous_master = True
                    settings.synchronous_mode = True
                    settings.fixed_delta_seconds = 0.05
                else:
                    synchronous_master = False
            else:
                print("You are currently in asynchronous mode. If this is a traffic simulation, \
                you could experience some issues. If it's not working correctly, switch to synchronous \
                mode by using traffic_manager.set_synchronous_mode(True)")

            if self.no_rendering:
                settings.no_rendering_mode = True
            world.apply_settings(settings)
            blueprints = get_actor_blueprints(world, self.filterv, self.generationv)
            blueprintsWalkers = get_actor_blueprints(world, self.filterw, self.generationw)

            if self.safe:
                blueprints = [x for x in blueprints if x.get_attribute('base_type') == 'car']

            blueprints = sorted(blueprints, key=lambda bp: bp.id)

            spawn_points = world.get_map().get_spawn_points()
            number_of_spawn_points = len(spawn_points)

            if self.number_of_vehicles < number_of_spawn_points:
                random.shuffle(spawn_points)
            elif self.number_of_vehicles > number_of_spawn_points:
                msg = 'requested %d vehicles, but could only find %d spawn points'
                logging.warning(msg, self.number_of_vehicles, number_of_spawn_points)
                self.number_of_vehicles = number_of_spawn_points

            # @todo cannot import these directly.
            SpawnActor = carla.command.SpawnActor
            SetAutopilot = carla.command.SetAutopilot
            FutureActor = carla.command.FutureActor

            # --------------
            # Spawn vehicles
            # --------------
            batch = []
            hero = self.hero
            for n, transform in enumerate(spawn_points):
                if n >= self.number_of_vehicles:
                    break
                blueprint = random.choice(blueprints)
                if blueprint.has_attribute('color'):
                    color = random.choice(blueprint.get_attribute('color').recommended_values)
                    blueprint.set_attribute('color', color)
                if blueprint.has_attribute('driver_id'):
                    driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
                    blueprint.set_attribute('driver_id', driver_id)
                if hero:
                    blueprint.set_attribute('role_name', 'hero')
                    hero = False
                else:
                    blueprint.set_attribute('role_name', 'autopilot')

                # spawn the cars and set their autopilot and light state all together
                batch.append(SpawnActor(blueprint, transform)
                    .then(SetAutopilot(FutureActor, True, traffic_manager.get_port())))

            for response in client.apply_batch_sync(batch, synchronous_master):
                if response.error:
                    logging.error(response.error)
                else:
                    vehicles_list.append(response.actor_id)

            # Set automatic vehicle lights update if specified
            if self.car_lights_on:
                all_vehicle_actors = world.get_actors(vehicles_list)
                for actor in all_vehicle_actors:
                    traffic_manager.update_vehicle_lights(actor, True)

            # -------------
            # Spawn Walkers
            # -------------
            # some settings
            percentagePedestriansRunning = 0.0      # how many pedestrians will run
            percentagePedestriansCrossing = 0.0     # how many pedestrians will walk through the road
            if self.seedw:
                world.set_pedestrians_seed(self.seedw)
                random.seed(self.seedw)
            # 1. take all the random locations to spawn
            spawn_points = []
            for i in range(self.number_of_walkers):
                spawn_point = carla.Transform()
                loc = world.get_random_location_from_navigation()
                if (loc != None):
                    spawn_point.location = loc
                    spawn_points.append(spawn_point)
            # 2. we spawn the walker object
            batch = []
            walker_speed = []
            for spawn_point in spawn_points:
                walker_bp = random.choice(blueprintsWalkers)
                # set as not invincible
                if walker_bp.has_attribute('is_invincible'):
                    walker_bp.set_attribute('is_invincible', 'false')
                # set the max speed
                if walker_bp.has_attribute('speed'):
                    if (random.random() > percentagePedestriansRunning):
                        # walking
                        walker_speed.append(walker_bp.get_attribute('speed').recommended_values[1])
                    else:
                        # running
                        walker_speed.append(walker_bp.get_attribute('speed').recommended_values[2])
                else:
                    print("Walker has no speed")
                    walker_speed.append(0.0)
                batch.append(SpawnActor(walker_bp, spawn_point))
            results = client.apply_batch_sync(batch, True)
            walker_speed2 = []
            for i in range(len(results)):
                if results[i].error:
                    logging.error(results[i].error)
                else:
                    walkers_list.append({"id": results[i].actor_id})
                    walker_speed2.append(walker_speed[i])
            walker_speed = walker_speed2
            # 3. we spawn the walker controller
            batch = []
            walker_controller_bp = world.get_blueprint_library().find('controller.ai.walker')
            for i in range(len(walkers_list)):
                batch.append(SpawnActor(walker_controller_bp, carla.Transform(), walkers_list[i]["id"]))
            results = client.apply_batch_sync(batch, True)
            for i in range(len(results)):
                if results[i].error:
                    logging.error(results[i].error)
                else:
                    walkers_list[i]["con"] = results[i].actor_id
            # 4. we put together the walkers and controllers id to get the objects from their id
            for i in range(len(walkers_list)):
                all_id.append(walkers_list[i]["con"])
                all_id.append(walkers_list[i]["id"])
            all_actors = world.get_actors(all_id)

            # wait for a tick to ensure client receives the last transform of the walkers we have just created
            if self.asynch or not synchronous_master:
                world.wait_for_tick()
            else:
                world.tick()

            # 5. initialize each controller and set target to walk to (list is [controler, actor, controller, actor ...])
            # set how many pedestrians can cross the road
            world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
            for i in range(0, len(all_id), 2):
                # start walker
                all_actors[i].start()
                # set walk to random point
                all_actors[i].go_to_location(world.get_random_location_from_navigation())
                # max speed
                all_actors[i].set_max_speed(float(walker_speed[int(i/2)]))

            print('spawned %d vehicles and %d walkers, press Ctrl+C to exit.' % (len(vehicles_list), len(walkers_list)))

            # Example of how to use Traffic Manager parameters
            traffic_manager.global_percentage_speed_difference(10.0)

            with open('vehicle_data.csv', 'w', newline='') as csvfile:
                fieldnames = [
                    "Vehicle Speed",
                    "Vehicle Acceleration",
                    "Vehicle Throttle",
                    "Vehicle Brake",
                    "Vehicle Steer",
                    "Vehicle Gear",
                    "Vehicle Manual Gear Shift",
                    "Vehicle Hand Brake"
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header row to CSV file
                writer.writeheader()

                # Main loop
                count = 0
                arr = []
                while count < 10:
                    if not self.asynch and synchronous_master:
                        world.tick()
                        all_vehicle_actors = world.get_actors(vehicles_list)
                        for i in all_vehicle_actors:
                            torque_curve_data = []
                            for vector in i.get_physics_control().torque_curve:
                                x_value = vector.x
                                y_value = vector.y
                                torque_curve_data.append((x_value, y_value))
                            this_world = i.get_world()
                            predictor = FuelConsumptionPredictor()
                            prediction = predictor.predict(50.0, 60.0, 1, 1, 0, 1)
                            #     def predict(self, distance, speed, gas_type, AC, rain, sun):
                            print("Predicted fuel consumption:", prediction)

                            vehicle_info = {
                                "Vehicle Speed": i.get_velocity().length(),
                                "Vehicle Acceleration": i.get_acceleration().length(),
                                "Vehicle Throttle": i.get_control().throttle,
                                "Vehicle Brake": i.get_control().brake,
                                "Vehicle Steer": i.get_control().steer,
                                "Vehicle Gear": i.get_control().gear,
                                "Vehicle Manual Gear Shift": i.get_control().manual_gear_shift,
                                "Vehicle Hand Brake": i.get_control().hand_brake,
                                "tire friction of tire 1": i.get_physics_control().wheels[0].tire_friction,
                                "max_rpm": i.get_physics_control().max_rpm,
                                "torque_curve": torque_curve_data,
                                "accelerometer": i.get_acceleration().length(), 
                            }
                            # Write vehicle_info to CSV file
                            pprint.pprint(vehicle_info)
                            arr.append(vehicle_info)
                            count += 1

                    else:
                        world.wait_for_tick()
        

        finally:

            if not self.asynch and synchronous_master:
                settings = world.get_settings()
                settings.synchronous_mode = False
                settings.no_rendering_mode = False
                settings.fixed_delta_seconds = None
                world.apply_settings(settings)

            print('\ndestroying %d vehicles' % len(vehicles_list))
            client.apply_batch([carla.command.DestroyActor(x) for x in vehicles_list])

            # stop walker controllers (list is [controller, actor, controller, actor ...])
            for i in range(0, len(all_id), 2):
                all_actors[i].stop()

            print('\ndestroying %d walkers' % len(walkers_list))
            client.apply_batch([carla.command.DestroyActor(x) for x in all_id])
            return arr    
            time.sleep(0.5)


if __name__ == '__main__':

    try:
        traffic1 = GenerateTraffic(number_of_vehicles=2)
        traffic1.start_traffic()
    except KeyboardInterrupt:
        pass
    finally:
        print('\ndone.')
